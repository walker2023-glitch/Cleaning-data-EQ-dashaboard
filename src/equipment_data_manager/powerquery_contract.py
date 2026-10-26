"""Offline reference checks for the companion M query; no Power BI connection.

This tests the input contract in Python, not execution of Microsoft's M runtime.
Production-mode rejection is deliberate: current app outputs remain unapproved.
"""

import argparse
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import Path
import re

from equipment_data_manager.processing.models import ProcessingError, ReportType
from equipment_data_manager.processing.powerbi import EXPORT_VERSION, schema


def read_table(raw: bytes, kind: ReportType, *, allow_candidates=False, financial_summary=False):
    try:
        table = list(csv.reader(StringIO(raw.decode('utf-8-sig'), newline=''), strict=True))
        contract = schema(kind)
        version, schema_version, report_name = EXPORT_VERSION, '1', kind.value
        if financial_summary:
            from equipment_data_manager.processing.repair_financial import SUMMARY_COLUMNS
            from equipment_data_manager.processing.interfaces import ColumnSchema
            integers = {'ReportedRepairCount', 'SourceRecordCount', 'RetainedRepairCount', 'UnavailableRepairCostCount'}
            numbers = {'ReportedLaborCost', 'ReportedPartsCost', 'ReportedTotalCost', 'KnownRepairTotalCost',
                       'RepairTotalDifference', 'SummaryComponentsDifference'}
            contract = tuple(ColumnSchema(n, 'integer' if n in integers else 'decimal' if n in numbers else 'text')
                             for n in SUMMARY_COLUMNS)
            version, schema_version, report_name = 'powerbi-v2', '2', 'repair_financial_summary'
        elif kind == ReportType.REPAIRS and table and 'FinancialSummarySHA256' in table[0]:
            from equipment_data_manager.processing.repair_financial import schema as v2_schema
            contract = v2_schema()
            version, schema_version = 'powerbi-v2', '2'
        if not table or table[0] != [c.name for c in contract] or len(table) < 2:
            raise ValueError
        result = []
        for row in table[1:]:
            if len(row) != len(contract):
                raise ValueError
            values = {}
            for column, value in zip(contract, row):
                if column.data_type == 'date':
                    parsed = date.fromisoformat(value) if value else None
                    if parsed and parsed.isoformat() != value:
                        raise ValueError
                elif column.data_type in ('integer', 'decimal'):
                    parsed = Decimal(value) if value else None
                    if parsed is not None and (not parsed.is_finite() or
                            (column.data_type == 'integer' and parsed != parsed.to_integral_value())):
                        raise ValueError
                else:
                    parsed = value
                values[column.name] = parsed
            if (values['ReportType'] != report_name or values['ExportVersion'] != version
                    or values['SchemaVersion'] != schema_version or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', values['ReportMonth'])
                    or values['ValidationStatus'] not in (('CandidateUnverified',) if allow_candidates else ('Approved',))):
                raise ValueError
            date.fromisoformat(values['ReportMonth'] + '-01')
            result.append(values)
        if len({r['ReportMonth'] for r in result}) != 1 or (len(result) != 1 if financial_summary else len({r['RecordId'] for r in result}) != len(result)):
            raise ValueError
        return result
    except (ValueError, UnicodeError, csv.Error, InvalidOperation):
        raise ProcessingError('folder_ingestion_contract_rejected') from None


def read_folder(folder: Path, kind: ReportType, *, allow_candidates=False):
    """Direct CSVs only; a superseded file with a second month key fails closed."""
    result, months, identifiers, versions = [], set(), set(), set()
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.suffix.lower() == '.csv' and not path.name.startswith(('.', '~')):
            if path.is_symlink():
                raise ProcessingError('folder_ingestion_link_rejected')
            rows = read_table(path.read_bytes(), kind, allow_candidates=allow_candidates)
            versions.add(rows[0]['SchemaVersion'])
            if len(versions) > 1:
                raise ProcessingError('folder_ingestion_mixed_schema_versions')
            month = rows[0]['ReportMonth']
            if month in months or any(r['RecordId'] in identifiers for r in rows):
                raise ProcessingError('folder_ingestion_duplicate_month_or_record')
            months.add(month)
            identifiers.update(r['RecordId'] for r in rows)
            result.extend(rows)
    if not result:
        raise ProcessingError('folder_ingestion_no_files')
    return result


def main():
    parser = argparse.ArgumentParser(description='Offline folder contract check; never publishes or refreshes Power BI')
    parser.add_argument('folder', type=Path)
    parser.add_argument('report_type', choices=[kind.value for kind in ReportType])
    parser.add_argument('--candidate-review', action='store_true', help='Explicit nonproduction review only')
    args = parser.parse_args()
    try:
        rows = read_folder(args.folder, ReportType(args.report_type), allow_candidates=args.candidate_review)
    except (ProcessingError, OSError):
        parser.exit(1, 'Folder rejected. Check schema, month duplicates, types, approval status and local availability.\n')
    print(f'{len(rows)} rows passed offline contract checks. This does not approve data or verify synchronization.')


if __name__ == '__main__':
    main()
