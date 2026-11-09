"""Explicit offline local TMA inspection. No candidate store or source-cell output."""
import argparse
from datetime import timedelta
from hashlib import sha256
import json
from pathlib import Path
import sys

from equipment_data_manager.processing import work_orders as tma
from equipment_data_manager.processing.cleaners import validate_period
from equipment_data_manager.processing.models import ProcessingError
from equipment_data_manager.storage.local import read_local_file


def runtime_info():
    import pandas
    import xlrd
    module_path = Path(tma.__file__)
    return dict(diagnostic_build=tma.STRUCTURE_DIAGNOSTIC_VERSION,
                python_executable=sys.executable, python_version=sys.version.split()[0],
                module_path=str(module_path),
                module_sha256=sha256(module_path.read_bytes()).hexdigest() if module_path.is_file() else None,
                cleaner_version=tma.TmaXlsxCleaner().version,
                pandas_version=pandas.__version__, xlrd_version=xlrd.__version__,
                note='Git HEAD is separate evidence; these fields identify the actually loaded module.')


def inspect_structure(content, *, extension, period):
    """Only dimension counts, fixed predicate labels, booleans and safe categories.

    Uses exactly the same captured bytes, reader and cleaner as preview, without
    creating SQLite/output/review/token state. No values, actual sheet/header/title,
    source filename/path/hash, record identifiers, names or descriptions are emitted.
    """
    report = dict(diagnostic_build=tma.STRUCTURE_DIAGNOSTIC_VERSION,
                  candidate_files_written=False, source_modified=False)
    try:
        validate_period(period)
        if extension != '.xls':
            raise ProcessingError('tma_timestamped_extension_mismatch')
        if len(content) > 64 * 1024 * 1024:
            raise ProcessingError('work_order_file_too_large')
        raw, _, meta = tma.read_workbook(content, extension, include_metadata=True)
        report.update(biff_version=meta.get('biff_version'), sheet_count=meta.get('sheet_count'),
                      formatting_dimensions=[meta.get('formatting_rows'), meta.get('formatting_columns')],
                      content_dimensions=[meta.get('physical_rows'), meta.get('physical_columns')],
                      parsed_dimensions=list(raw.shape), timestamp_cell_type=meta.get('timestamp_kind'),
                      excel_datemode=meta.get('timestamp_datemode'))
        report['structure_checks'] = [dict(failure_code=code, passed=bool(value))
            for code,value in tma.timestamped_structure_checks(raw, meta, extension).items()]
        checks = {}
        report['checks'] = checks
        try:
            generated = tma.generation_timestamp(meta)
            checks['numeric_generation_timestamp_valid'] = True
            checks['generation_previous_month_matches'] = (generated.replace(day=1) - timedelta(days=1)).strftime('%Y-%m') == period
        except ProcessingError:
            checks['numeric_generation_timestamp_valid'] = False
        if raw.shape[1] == 4 and len(raw) >= 4:
            checks['timestamp_other_cells_blank'] = not raw.iloc[0, 1:].ne('').any()
            checks['exact_title_matches'] = raw.iat[1, 0] == tma.TIMESTAMPED_TITLE and not raw.iloc[1, 1:].ne('').any()
            checks['separator_is_blank'] = not raw.iloc[2].ne('').any()
            checks['exact_headers_match'] = raw.iloc[3].tolist() == tma.requests.REQUEST_COLUMNS[:-1]
        result = tma.TmaXlsxCleaner().clean(content, source_name='diagnostic.xls', period=period)
        report.update(preview_status='success', input_records=result.input_rows, retained_records=result.output_rows,
                      warnings=list(result.warnings))
    except ProcessingError as error:
        report.update(preview_status='failure', failure_code=str(error))
    except Exception:
        report.update(preview_status='failure', failure_code='tma_diagnostic_unavailable')
    # pandas/numpy predicates may return numpy bools. Export plain JSON values only.
    if 'checks' in report:
        report['checks'] = {key: bool(value) for key, value in report['checks'].items()}
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', action='store_true', help='Show loaded code/executable paths, build marker and module hash; no report is opened')
    parser.add_argument('--input', type=Path, help='Private local original XLS, read only')
    parser.add_argument('--period', help='Selected YYYY-MM')
    args = parser.parse_args(argv)
    if args.runtime:
        print(json.dumps(runtime_info(), indent=2))
        return 0
    if args.input is None or args.period is None:
        parser.error('Use --runtime, or supply --input and --period.')
    try:
        content = read_local_file(args.input).content
        report = inspect_structure(content, extension=args.input.suffix.lower(), period=args.period)
    except ProcessingError as error:
        report = dict(preview_status='failure', failure_code=str(error))
    except Exception:
        report = dict(preview_status='failure', failure_code='tma_diagnostic_unavailable')
    print(json.dumps(report, indent=2))
    return 0 if report['preview_status'] == 'success' else 1


if __name__ == '__main__':
    raise SystemExit(main())
