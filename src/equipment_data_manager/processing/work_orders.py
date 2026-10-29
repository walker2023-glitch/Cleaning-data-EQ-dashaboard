"""Strict local adapter for the observed TMA title/header/body/footer XLSX.

Uses the supplied requests transform and writer as a provisional candidate
contract. Neither this shape check nor count reconciliation is business approval.
No CSV or legacy XLS format is inferred from this XLSX sample.
"""

from decimal import Decimal
from hashlib import sha256
from io import BytesIO, StringIO
from pathlib import Path
import re
import warnings

import pandas as pd

from equipment_data_manager.processing._legacy import requests_row_clean as requests
from equipment_data_manager.processing.cleaners import validate_period
from equipment_data_manager.processing.interfaces import CleanResult, ColumnSchema, ReconciliationMetric
from equipment_data_manager.processing.models import ProcessingError


class TmaXlsxCleaner:
    def __init__(self):
        root = Path(__file__).parent / "_legacy"
        digest = sha256(b"".join((root / name).read_bytes() for name in
                                ("requests_row_clean.py", "row_clean_common.py"))).hexdigest()
        self.version = f"tma-xlsx-v1:pandas-{pd.__version__}:{digest}"

    def clean(self, raw_bytes: bytes, *, source_name: str, period: str) -> CleanResult:
        validate_period(period)
        if Path(source_name).suffix.lower() != ".xlsx":
            raise ProcessingError("unsupported_file_format")
        if not raw_bytes:
            raise ProcessingError("empty_input")
        try:
            with pd.ExcelFile(BytesIO(raw_bytes), engine="openpyxl") as workbook:
                if len(workbook.sheet_names) != 1:
                    raise ProcessingError("unsupported_work_order_layout")
                raw = pd.read_excel(workbook, header=None, dtype=str, keep_default_na=False)
        except ProcessingError:
            raise
        except Exception:
            raise ProcessingError("invalid_xlsx_file") from None
        if raw.shape[1] != 5 or len(raw) < 4:
            raise ProcessingError("unsupported_work_order_layout")
        label = pd.Period(period, freq="M").strftime("%B %Y")
        if raw.iloc[0, 0] != f"CU Repair WO History — {label}":
            raise ProcessingError("work_order_title_period_mismatch")
        if raw.iloc[0, 1:].ne("").any() or raw.iloc[1].tolist() != requests.REQUEST_COLUMNS:
            raise ProcessingError("unsupported_work_order_layout")
        footer = re.fullmatch(r"Total:\s*([0-9]+) records", str(raw.iloc[-1, 0]).strip())
        if footer is None or raw.iloc[-1, 1:].ne("").any():
            raise ProcessingError("invalid_work_order_summary")
        frame = raw.iloc[2:-1].copy()
        frame.columns = requests.REQUEST_COLUMNS
        count = int(footer.group(1))
        if count != len(frame):
            raise ProcessingError("work_order_summary_count_mismatch")
        notes = ["production_accuracy_unverified", "tma_output_contract_provisional"]
        # Observe exactly the same vectorized date parsing as the original.
        with warnings.catch_warnings(record=True) as parser_warnings:
            warnings.simplefilter("always")
            dates = pd.to_datetime(frame["Request Date"], errors="coerce")
            cleaned = requests.clean_requests_raw(frame)
        if parser_warnings:
            notes.append("legacy_parser_warnings")
        invalid = int(dates.isna().sum())
        if invalid:
            notes.append(f"invalid_source_dates:{invalid}")
        if len(cleaned) < len(frame):
            notes.append(f"rows_excluded_by_legacy:{len(frame) - len(cleaned)}")
        if cleaned.empty:
            raise ProcessingError("no_output_rows")
        if any(value[6:10] + "-" + value[:2] != period for value in cleaned["Request Date"]):
            raise ProcessingError("output_period_mismatch")
        output = StringIO(newline="")
        requests._write_requests_csv(cleaned, output, period)
        return CleanResult(
            output.getvalue().encode("utf-8"), len(frame), len(cleaned),
            tuple(ColumnSchema(str(name), str(dtype)) for name, dtype in cleaned.dtypes.items()),
            tuple(notes), period, self.version,
            (ReconciliationMetric("Source work orders", Decimal(count), "count"),
             ReconciliationMetric("Retained work orders", Decimal(len(cleaned)), "count")),
        )
