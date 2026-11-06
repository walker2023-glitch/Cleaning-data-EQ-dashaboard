"""Strict local adapter for TMA title/header/body/footer XLSX and BIFF8 XLS candidates.

Uses the supplied requests transform and writer as a provisional candidate
contract. Neither this shape check nor count reconciliation is business approval.
Four/five-column and the owner-described timestamped HI-042b layout share the
preserved transform. Actual workbook acceptance is still an owner-local check.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from io import BytesIO, StringIO
from pathlib import Path
import re
import math
import warnings

import pandas as pd

from equipment_data_manager.processing._legacy import requests_row_clean as requests
from equipment_data_manager.processing.cleaners import validate_period
from equipment_data_manager.processing.interfaces import CleanResult, ColumnSchema, ReconciliationMetric
from equipment_data_manager.processing.models import ProcessingError


def read_workbook(raw_bytes, extension, *, include_metadata=False):
    """No Office automation, formula/macro evaluation or external-link refresh.

    xlrd reads BIFF cell values only; openpyxl retains its existing cached-value
    behavior. Error text is category-only. A numeric ID's stored integer and an
    unambiguous zero-only number format may be preserved; missing zeros are never
    invented from General or arbitrary Excel formatting expressions.
    """
    is_xls = extension == '.xls'
    if is_xls and not raw_bytes.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
        raise ProcessingError('invalid_xls_file')
    notes, metadata = [], {}
    try:
        kwargs = {'formatting_info': True, 'on_demand': True, 'logfile': StringIO()} if is_xls else {}
        with pd.ExcelFile(BytesIO(raw_bytes), engine='xlrd' if is_xls else 'openpyxl',
                          engine_kwargs=kwargs) as workbook:
            if len(workbook.sheet_names) != 1:
                raise ProcessingError('unsupported_work_order_layout')
            metadata['sheet_name'] = workbook.sheet_names[0]
            if is_xls:
                import xlrd
                if workbook.book.biff_version != 80:
                    raise ProcessingError('unsupported_work_order_layout')
                sheet = workbook.book.sheet_by_index(0)
                if sheet.nrows > 100_003 or sheet.ncols not in (4, 5):
                    raise ProcessingError('unsupported_work_order_layout')
                if any(sheet.cell_type(r, c) == xlrd.XL_CELL_ERROR
                       for r in range(sheet.nrows) for c in range(sheet.ncols)):
                    raise ProcessingError('invalid_xls_file')
                metadata.update(physical_rows=sheet.nrows, physical_columns=sheet.ncols)
                if sheet.nrows:
                    first = sheet.cell(0, 0)
                    metadata['timestamp_kind'] = first.ctype
                    metadata['timestamp_value'] = first.value
                    metadata['timestamp_datemode'] = workbook.book.datemode
            raw = pd.read_excel(workbook, header=None, dtype=str, keep_default_na=False)
            if is_xls:
                notes.append('tma_xls_cached_values_only')
                timestamped = is_timestamped_layout(raw, metadata)
                first_row, stop_row = (4, len(raw)) if timestamped else (2, len(raw) - 1)
                for row in range(first_row, min(stop_row, sheet.nrows)):
                    cell = sheet.cell(row, 0)
                    if cell.ctype in (xlrd.XL_CELL_DATE, xlrd.XL_CELL_BOOLEAN):
                        raise ProcessingError('ambiguous_work_order_identifier')
                    if cell.ctype != xlrd.XL_CELL_NUMBER:
                        continue
                    value = cell.value
                    if not value.is_integer() or value < 0 or value > 2**53 - 1:
                        raise ProcessingError('ambiguous_work_order_identifier')
                    fmt_key = workbook.book.xf_list[cell.xf_index].format_key
                    fmt = workbook.book.format_map[fmt_key].format_str
                    if re.fullmatch(r'0{2,20}', fmt):
                        raw.iat[row, 0] = str(int(value)).zfill(len(fmt))
                    elif fmt in ('General', '0'):
                        raw.iat[row, 0] = str(int(value))
                        notes.append('tma_numeric_identifier_leading_zeros_not_inferable')
                    else:
                        raise ProcessingError('ambiguous_work_order_identifier')
        result = raw, tuple(dict.fromkeys(notes))
        return (*result, metadata) if include_metadata else result
    except ProcessingError:
        raise
    except Exception:
        raise ProcessingError('invalid_xls_file' if is_xls else 'invalid_xlsx_file') from None


TIMESTAMPED_SHEET = 'CU_Repair_WO_History_-_Previous'
TIMESTAMPED_TITLE = 'CU Repair WO History - Previous Month (HI-042b)'


def is_timestamped_layout(raw, metadata):
    # Multiple recognizable signals route malformed variants to specific rejection;
    # these hints NEVER establish acceptance of a Previous Month workbook.
    if len(raw) > 1 and raw.iloc[1].tolist() in (requests.REQUEST_COLUMNS, requests.REQUEST_COLUMNS[:-1]):
        return False  # Preserve the existing standard layout regardless of sheet name.
    return (metadata.get('sheet_name') == TIMESTAMPED_SHEET or
            (len(raw) > 1 and raw.iat[1, 0] == TIMESTAMPED_TITLE))


def generation_timestamp(metadata):
    """Exact numeric serial contract; text/localized timestamps are unsupported."""
    import xlrd
    value, mode = metadata.get('timestamp_value'), metadata.get('timestamp_datemode')
    if (metadata.get('timestamp_kind') not in (xlrd.XL_CELL_NUMBER, xlrd.XL_CELL_DATE)
            or type(value) not in (int, float) or not math.isfinite(value) or value < 1
            or type(mode) is not int or mode not in (0, 1)
            or (mode == 0 and 60 <= value < 61)):  # Excel's fictional 1900-02-29.
        raise ProcessingError('tma_generation_timestamp_invalid')
    try:
        generated = xlrd.xldate_as_datetime(value, mode)
        if not isinstance(generated, datetime) or generated.tzinfo is not None:
            raise ValueError
        return generated
    except (ValueError, OverflowError, xlrd.XLDateError):
        raise ProcessingError('tma_generation_timestamp_invalid') from None


def timestamped_body(raw, metadata, extension, period):
    """Owner-described HI-042b structure; no report-footer inference or slicing."""
    if (extension != '.xls' or metadata.get('sheet_name') != TIMESTAMPED_SHEET
            or metadata.get('physical_columns') != 4 or raw.shape[1] != 4
            or len(raw) < 5 or metadata.get('physical_rows') != len(raw)):
        raise ProcessingError('tma_timestamped_structure_invalid')
    if raw.iloc[0, 1:].ne('').any():
        raise ProcessingError('tma_generation_timestamp_invalid')
    generated = generation_timestamp(metadata)
    try:
        expected = (generated.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
    except (ValueError, OverflowError):
        raise ProcessingError('tma_generation_timestamp_invalid') from None
    if expected != period:
        raise ProcessingError('tma_generation_period_mismatch')
    if raw.iat[1, 0] != TIMESTAMPED_TITLE or raw.iloc[1, 1:].ne('').any():
        raise ProcessingError('tma_timestamped_title_invalid')
    if raw.iloc[2].ne('').any():
        raise ProcessingError('tma_timestamped_separator_invalid')
    if raw.iloc[3].tolist() != requests.REQUEST_COLUMNS[:-1]:
        raise ProcessingError('tma_timestamped_headers_invalid')
    frame = raw.iloc[4:].copy()
    frame.columns = requests.REQUEST_COLUMNS[:-1]
    # Known summary/footer markers are structural errors in this no-footer layout,
    # while ordinary records still use the original ID/date exclusion rules.
    if frame['Work Order #'].astype(str).str.strip().str.match(r'(?i)^(?:grand\s+)?total(?:$|[\s:])').any():
        raise ProcessingError('tma_timestamped_unexpected_footer')
    return frame, generated


class TmaXlsxCleaner:
    def __init__(self):
        root = Path(__file__).parent / "_legacy"
        digest = sha256(b"".join((root / name).read_bytes() for name in
                                ("requests_row_clean.py", "row_clean_common.py"))).hexdigest()
        self.version = f"tma-workbook-v3:xlrd-2.0.2:pandas-{pd.__version__}:{digest}"

    def clean(self, raw_bytes: bytes, *, source_name: str, period: str) -> CleanResult:
        validate_period(period)
        extension = Path(source_name).suffix.lower()
        if extension not in (".xlsx", ".xls"):
            raise ProcessingError("unsupported_file_format")
        if not raw_bytes:
            raise ProcessingError("empty_input")
        if len(raw_bytes) > 64 * 1024 * 1024:
            raise ProcessingError('work_order_file_too_large')
        raw, reader_notes, metadata = read_workbook(raw_bytes, extension, include_metadata=True)
        timestamped = is_timestamped_layout(raw, metadata)
        generated = None
        if timestamped:
            frame, generated = timestamped_body(raw, metadata, extension, period)
            missing_assignment = True
            count = len(frame)
        else:
            if raw.shape[1] not in (4, 5) or len(raw) < 4:
                raise ProcessingError("unsupported_work_order_layout")
            label = pd.Period(period, freq="M").strftime("%B %Y")
            if raw.iloc[0, 0] != f"CU Repair WO History — {label}":
                raise ProcessingError("work_order_title_period_mismatch")
            columns = raw.iloc[1].tolist()
            missing_assignment = columns == requests.REQUEST_COLUMNS[:-1]
            if raw.iloc[0, 1:].ne("").any() or columns not in (requests.REQUEST_COLUMNS, requests.REQUEST_COLUMNS[:-1]):
                raise ProcessingError("unsupported_work_order_layout")
            footer = re.fullmatch(r"Total:\s*([0-9]+) records", str(raw.iloc[-1, 0]).strip())
            if footer is None or raw.iloc[-1, 1:].ne("").any():
                raise ProcessingError("invalid_work_order_summary")
            frame = raw.iloc[2:-1].copy()
            frame.columns = columns
            count = int(footer.group(1))
            if count != len(frame):
                raise ProcessingError("work_order_summary_count_mismatch")
        notes = ["production_accuracy_unverified", "tma_output_contract_provisional", *reader_notes]
        if timestamped:
            notes.append('tma_timestamped_previous_month_layout')
        if missing_assignment:
            notes.extend(["tma_assigned_to_source_column_missing",
                f"tma_assigned_to_source_column_missing_records:{len(frame)}"])
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
        outside = int((dates.notna() & dates.dt.to_period('M').astype(str).ne(period)).sum())
        if outside:
            notes.append(f'tma_cross_period_source_dates:{outside}')
        if len(cleaned) < len(frame):
            notes.append(f"rows_excluded_by_legacy:{len(frame) - len(cleaned)}")
        if cleaned.empty:
            raise ProcessingError("no_output_rows")
        if any(value[6:10] + "-" + value[:2] != period for value in cleaned["Request Date"]):
            raise ProcessingError("output_period_mismatch")
        if missing_assignment:
            notes.append(f"tma_assigned_to_source_column_missing_retained:{len(cleaned)}")
        if timestamped:
            notes.extend([f'tma_physical_worksheet_rows:{metadata["physical_rows"]}',
                          f'tma_parseable_source_request_dates:{len(frame) - invalid}'])
        metrics = [ReconciliationMetric("Source work orders", Decimal(count), "count"),
                   ReconciliationMetric("Retained work orders", Decimal(len(cleaned)), "count")]
        if missing_assignment:
            metrics.append(ReconciliationMetric("Retained work orders missing source Assigned To", Decimal(len(cleaned)), "count"))
        if timestamped:
            metrics.extend([ReconciliationMetric("Physical worksheet rows", Decimal(metadata['physical_rows']), "count"),
                ReconciliationMetric("Parseable source request dates", Decimal(len(frame) - invalid), "count"),
                ReconciliationMetric("Source request dates outside selected month", Decimal(outside), "count")])
        output = StringIO(newline="")
        requests._write_requests_csv(cleaned, output, period)
        return CleanResult(
            output.getvalue().encode("utf-8"), len(frame), len(cleaned),
            tuple(ColumnSchema(str(name), str(dtype)) for name, dtype in cleaned.dtypes.items()),
            tuple(notes), period, self.version,
            tuple(metrics),
        )
