"""Strict local adapter for TMA title/header/body/footer XLSX and BIFF8 XLS candidates.

Uses the supplied requests transform and writer as a provisional candidate
contract. Neither this shape check nor count reconciliation is business approval.
Four/five-column candidates share the preserved original transform. Actual May
layout equivalence is unverified until owner acceptance; unknown titles fail closed.
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


def read_workbook(raw_bytes, extension):
    """No Office automation, formula/macro evaluation or external-link refresh.

    xlrd reads BIFF cell values only; openpyxl retains its existing cached-value
    behavior. Error text is category-only. A numeric ID's stored integer and an
    unambiguous zero-only number format may be preserved; missing zeros are never
    invented from General or arbitrary Excel formatting expressions.
    """
    is_xls = extension == '.xls'
    if is_xls and not raw_bytes.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
        raise ProcessingError('invalid_xls_file')
    notes = []
    try:
        kwargs = {'formatting_info': True, 'on_demand': True, 'logfile': StringIO()} if is_xls else {}
        with pd.ExcelFile(BytesIO(raw_bytes), engine='xlrd' if is_xls else 'openpyxl',
                          engine_kwargs=kwargs) as workbook:
            if len(workbook.sheet_names) != 1:
                raise ProcessingError('unsupported_work_order_layout')
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
            raw = pd.read_excel(workbook, header=None, dtype=str, keep_default_na=False)
            if is_xls:
                notes.append('tma_xls_cached_values_only')
                for row in range(2, min(len(raw) - 1, sheet.nrows)):
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
        return raw, tuple(dict.fromkeys(notes))
    except ProcessingError:
        raise
    except Exception:
        raise ProcessingError('invalid_xls_file' if is_xls else 'invalid_xlsx_file') from None


class TmaXlsxCleaner:
    def __init__(self):
        root = Path(__file__).parent / "_legacy"
        digest = sha256(b"".join((root / name).read_bytes() for name in
                                ("requests_row_clean.py", "row_clean_common.py"))).hexdigest()
        self.version = f"tma-workbook-v2:xlrd-2.0.2:pandas-{pd.__version__}:{digest}"

    def clean(self, raw_bytes: bytes, *, source_name: str, period: str) -> CleanResult:
        validate_period(period)
        extension = Path(source_name).suffix.lower()
        if extension not in (".xlsx", ".xls"):
            raise ProcessingError("unsupported_file_format")
        if not raw_bytes:
            raise ProcessingError("empty_input")
        if len(raw_bytes) > 64 * 1024 * 1024:
            raise ProcessingError('work_order_file_too_large')
        raw, reader_notes = read_workbook(raw_bytes, extension)
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
        output = StringIO(newline="")
        requests._write_requests_csv(cleaned, output, period)
        return CleanResult(
            output.getvalue().encode("utf-8"), len(frame), len(cleaned),
            tuple(ColumnSchema(str(name), str(dtype)) for name, dtype in cleaned.dtypes.items()),
            tuple(notes), period, self.version,
            (ReconciliationMetric("Source work orders", Decimal(count), "count"),
             ReconciliationMetric("Retained work orders", Decimal(len(cleaned)), "count"),
             *( (ReconciliationMetric("Retained work orders missing source Assigned To", Decimal(len(cleaned)), "count"),)
                if missing_assignment else () )),
        )
