"""Conservative CSV wrappers around source-preserved CompuClean transforms."""

import csv
from decimal import Decimal
from hashlib import sha256
from io import BytesIO, StringIO
import math
from pathlib import Path
import re
import warnings

import pandas as pd

from equipment_data_manager.processing._legacy import repairs_row_clean as repairs
from equipment_data_manager.processing._legacy import service_row_clean as service
from equipment_data_manager.processing.interfaces import CleanResult, ColumnSchema, ReconciliationMetric
from equipment_data_manager.processing.models import ProcessingError, ReportType
from equipment_data_manager.processing.repair_layouts import SummaryRepairsLayout
from equipment_data_manager.processing.service_layouts import SummaryServiceOrdersLayout


def validate_period(period: str) -> None:
    if not isinstance(period, str) or not re.fullmatch(r"[1-9][0-9]{3}-(0[1-9]|1[0-2])", period):
        raise ProcessingError("invalid_reporting_period")


def read_csv(raw: bytes, *, service_export: bool = False, repair_export: bool = False) -> pd.DataFrame:
    """Check layout before pandas can silently rename duplicate headers.

    Preserve legacy pandas inference/NA handling for accepted UTF-8 CSVs. Other
    encodings and non-header-first layouts require evidence before support.
    """
    if not raw or not raw.strip():
        raise ProcessingError("empty_input")
    if b"\x00" in raw:
        raise ProcessingError("invalid_csv_or_encoding")
    try:
        text = raw.decode("utf-8-sig", errors="strict")
        records = csv.reader(StringIO(text, newline=""), strict=True)
        header = next(records)
        if not header or any(not name.strip() for name in header):
            raise ProcessingError("blank_headers")
        normalized = [name.strip() for name in header]
        if len(set(normalized)) != len(normalized):
            raise ProcessingError("duplicate_headers")
        # Do not silently normalize aliases or whitespace in the repair reader.
        if header != normalized:
            raise ProcessingError("unverified_header_layout")
        for row in records:
            if row and len(row) != len(header):
                raise ProcessingError("invalid_csv_row_width")
        # Only the newly observed layout uses an explicit ID dtype. Preserve
        # inference for previously supported layouts to keep their behavior stable.
        dtype = {"EquipmentId1": str} if service_export and SummaryServiceOrdersLayout.matches(header) else None
        if repair_export and SummaryRepairsLayout.matches(header):
            dtype = {"PersonnelId1": str}
        return pd.read_csv(BytesIO(raw), encoding_errors="replace", dtype=dtype)
    except (UnicodeError, csv.Error, StopIteration, pd.errors.ParserError, pd.errors.EmptyDataError):
        raise ProcessingError("invalid_csv_or_encoding") from None


class LegacyCsvCleaner:
    """Only flat, header-first repairs/service CSVs are enabled in M1.

    Required-column gates are conservative supported-layout constraints, not an
    assertion that real departmental reports have a verified required schema.
    """

    def __init__(self, report_type: ReportType):
        if report_type not in (ReportType.REPAIRS, ReportType.SERVICE_ORDERS):
            raise ProcessingError("report_type_awaiting_verified_fixtures")
        self.report_type = report_type
        source_files = ("row_clean_common.py", "repairs_row_clean.py", "service_row_clean.py")
        root = Path(__file__).parent / "_legacy"
        source_hash = sha256(b"".join((root / name).read_bytes() for name in source_files)).hexdigest()
        # Bump this version if reading, formatting or validation policy changes.
        wrapper_version = "wrapper-v4-service-diagnostics" if report_type == ReportType.SERVICE_ORDERS else "wrapper-v3-repair-summary"
        self.version = f"{wrapper_version}:pandas-{pd.__version__}:{source_hash}"

    def clean(self, raw_bytes: bytes, *, source_name: str, period: str) -> CleanResult:
        validate_period(period)
        if Path(source_name).suffix.lower() != ".csv":
            raise ProcessingError("unsupported_file_format")
        frame = read_csv(raw_bytes, service_export=self.report_type == ReportType.SERVICE_ORDERS,
                         repair_export=self.report_type == ReportType.REPAIRS)
        notes = ["production_accuracy_unverified"]
        source_service_count = None
        source_repair_metrics = ()
        if self.report_type == ReportType.REPAIRS and SummaryRepairsLayout.matches(frame.columns):
            source_repair_metrics = SummaryRepairsLayout.metrics(frame)
        if self.report_type == ReportType.SERVICE_ORDERS and SummaryServiceOrdersLayout.matches(frame.columns):
            frame, source_service_count = SummaryServiceOrdersLayout.prepare(frame)
            notes.append("estimated_price_unavailable")
            fallback = sum(str(value).strip().lower() not in {"scheduled", "completed"}
                           for value in frame["Textbox21"])
            if fallback:
                notes.append(f"service_status_inferred:{fallback}")
        if self.report_type == ReportType.REPAIRS:
            required = {
                "PersonnelId5", "PersonnelId1", "CompletedDate1", "PersonnelId4",
                "PersonnelId3", "Textbox38", "Details",
            }
            date_fields, money_field = ("CompletedDate1",), "Textbox38"
        else:
            required = {
                "EquipmentId1", "EquipmentName1", "ScheduledDate", "CompletedDate",
                "Description", "Cost", "Textbox21",
            }
            if not ({"Name", "Location"} & set(frame.columns)):
                raise ProcessingError("missing_required_columns")
            # Two competing location aliases would create an ambiguous layout.
            if {"Name", "Location"} <= set(frame.columns):
                raise ProcessingError("ambiguous_service_layout")
            if {"EquipmentId", "EquipmentName", "StatusRaw"} & set(frame.columns):
                raise ProcessingError("ambiguous_service_layout")
            date_fields, money_field = ("ScheduledDate", "CompletedDate"), "Cost"
        if not required <= set(frame.columns):
            raise ProcessingError("missing_required_columns")
        recognized = required | ({"Name", "Location"} if self.report_type == ReportType.SERVICE_ORDERS else set())
        if source_service_count is not None:
            recognized.add("Textbox56")  # Consumed as count metadata, never as a row or price.
        if source_repair_metrics:
            recognized |= {"Textbox10", "Textbox11", "Textbox12", "Textbox13"}
        unknown = len(set(frame.columns) - recognized)
        if unknown:
            notes.append(f"unmapped_source_columns:{unknown}")

        # Diagnostics observe parsing; they do not replace or change legacy rules.
        with warnings.catch_warnings(record=True) as parser_warnings:
            warnings.simplefilter("always")
            bad_dates = 0
            for column in date_fields:
                for value in frame[column]:
                    if pd.notna(value) and str(value).strip():
                        if pd.isna(pd.to_datetime(value, errors="coerce")):
                            bad_dates += 1
            cleaned = (
                repairs.clean_repairs_raw(frame)
                if self.report_type == ReportType.REPAIRS
                else service.clean_service_raw(frame, period)
            )
        if parser_warnings:
            notes.append("legacy_parser_warnings")
        if bad_dates:
            notes.append(f"invalid_source_dates:{bad_dates}")
        invalid_money = 0
        for value in frame[money_field]:
            if pd.notna(value) and str(value).strip():
                number = pd.to_numeric(str(value).strip().replace("$", "").replace(",", ""), errors="coerce")
                if pd.isna(number) or not math.isfinite(float(number)):
                    invalid_money += 1
        if invalid_money:
            notes.append(f"invalid_source_money:{invalid_money}")
        if self.report_type == ReportType.REPAIRS:
            notes.append("legacy_duration_defaults_and_rate_unverified")
        if len(cleaned) < len(frame):
            notes.append(f"rows_excluded_by_legacy:{len(frame) - len(cleaned)}")
        if cleaned.empty:
            raise ProcessingError("no_output_rows")

        self._validate_candidate(cleaned, period)
        if self.report_type == ReportType.SERVICE_ORDERS:
            cross_period = sum(
                bool(value) and str(value)[:7] != period
                for column in ("Sched. Date", "Completed Date") for value in cleaned[column]
            )
            if cross_period:
                notes.append(f"cross_period_output_dates:{cross_period}")
        output = StringIO(newline="")
        if self.report_type == ReportType.REPAIRS:
            # Reuse the exact existing writer, including its three-row preamble.
            title = f"BYU–Idaho  |  Equipment Repair Log  |  {pd.Period(period, freq='M').strftime('%B %Y')}"
            repairs._write_repairs_csv(cleaned, output, title)
            metrics = tuple(
                ReconciliationMetric(column, sum((Decimal(str(v)) for v in cleaned[column]), Decimal(0)), unit)
                for column, unit in (
                    ("# of Repairs", "count"), ("Repair Person-Hrs", "hours"),
                    ("Parts Cost $", "legacy_dollars"), ("Total Labor $", "legacy_dollars"),
                    ("Est. Total $", "legacy_dollars"),
                )
            )
            if source_repair_metrics:
                reported = {metric.name: metric.value for metric in source_repair_metrics}
                calculated = {metric.name: metric.value for metric in metrics}
                if any(reported[source] != calculated[target] for source, target in (
                    ("Source reported labor", "Total Labor $"),
                    ("Source reported parts", "Parts Cost $"),
                    ("Source reported cost", "Est. Total $"),
                )):
                    notes.append("repair_source_totals_differ")
                notes.append("repair_cost_mapping_unverified")
                metrics += source_repair_metrics
        else:
            cleaned.to_csv(output, index=False)
            metrics = (
                ReconciliationMetric("Source service orders", Decimal(source_service_count), "count"),
                ReconciliationMetric("Retained service orders", Decimal(len(cleaned)), "count"),
            ) if source_service_count is not None else ()
        return CleanResult(
            output.getvalue().encode("utf-8"), len(frame), len(cleaned),
            tuple(ColumnSchema(str(name), str(dtype)) for name, dtype in cleaned.dtypes.items()),
            tuple(notes), period, self.version, metrics,
        )

    def _validate_candidate(self, frame: pd.DataFrame, period: str) -> None:
        if self.report_type == ReportType.REPAIRS:
            if any(str(value)[:7] != period for value in frame["Completed Date"]):
                # Do not silently add a new filtering rule to the legacy cleaner.
                raise ProcessingError("output_period_mismatch")
            for column in ("Repair Person-Hrs", "Parts Cost $", "Total Labor $", "Est. Total $"):
                if any(not math.isfinite(float(value)) for value in frame[column]):
                    raise ProcessingError("nonfinite_output_number")
        else:
            for _, row in frame.iterrows():
                if period not in {str(row["Sched. Date"])[:7], str(row["Completed Date"])[:7]}:
                    raise ProcessingError("output_period_mismatch")
                price = row["Estimated Price"]
                if price != "" and not math.isfinite(float(price)):
                    raise ProcessingError("nonfinite_output_number")
