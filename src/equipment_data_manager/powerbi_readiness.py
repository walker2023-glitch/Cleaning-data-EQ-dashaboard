"""Offline assessment for a four-table, schema-v2 Power BI review snapshot.

Reads candidates/optional explicitly indexed raw files; writes new PRIVATE reports.
No cleaning, approval, publishing, authentication or Power BI execution.
"""
import argparse
import csv
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil

from equipment_data_manager.powerbi_pilot import _periods, _unlinked, read_snapshot
from equipment_data_manager.processing.models import ProcessingError, ReportType
from equipment_data_manager.settings import candidate_location_error

EXPECTATION_COLUMNS = ['period', 'report_type', 'metric', 'expected', 'tolerance', 'evidence']
SOURCE_COLUMNS = ['report_type', 'period', 'path']
REQUIRED = {
    'repairs': ('record_count', 'reported_total_cost', 'missing_reported_cost_count'),
    'service_orders': ('record_count',),
    'tma_work_orders': ('record_count',),
    'repair_financial_summary': ('reported_repair_count', 'reported_parts_cost', 'reported_labor_cost', 'reported_total_cost'),
}
PROVENANCE = ('ReportMonth', 'SourceSystem', 'ReportType', 'SourceFileName', 'SourceFileSHA256',
              'LegacyCandidateSHA256', 'CleanerVersion', 'ExportVersion', 'SchemaVersion', 'ValidationStatus')


@dataclass(repr=False)
class ReviewAssessment:
    controls: list = field(repr=False)
    comparisons: list = field(repr=False)
    files: list = field(repr=False)
    sources: list = field(repr=False)
    status: dict


def _same_provenance(rows, kind):
    first = rows[0]
    if (any(any(r[k] != first[k] for k in PROVENANCE) for r in rows)
            or first['SourceSystem'] != ('TMA' if kind == ReportType.TMA_WORK_ORDERS else 'CompuClean')
            or not first['SourceFileName'] or '/' in first['SourceFileName'] or '\\' in first['SourceFileName']
            or not first['CleanerVersion']
            or any(not re.fullmatch(r'[0-9a-f]{64}', first[k]) for k in ('SourceFileSHA256', 'LegacyCandidateSHA256'))
            or any(not re.fullmatch(r'[0-9a-f]{64}', r['RecordId']) for r in rows)
            or [r['CandidateRecordNumber'] for r in rows] != list(range(1, len(rows) + 1))):
        raise ProcessingError('readiness_source_provenance_rejected')


def _record_contract(rows, kind):
    from equipment_data_manager.processing.repair_financial import money
    dates = {ReportType.REPAIRS: ('CompletedDate',), ReportType.SERVICE_ORDERS: ('ScheduledDate', 'CompletedDate'),
             ReportType.TMA_WORK_ORDERS: ('RequestDate',)}[kind]
    for row in rows:
        # Same report-month semantics as existing adapters, including service OR.
        if not any(row[c] is not None and row[c].strftime('%Y-%m') == row['ReportMonth'] for c in dates):
            raise ProcessingError('readiness_record_period_rejected')
        if kind == ReportType.REPAIRS:
            value, status = row['ReportedTotalCost'], row['ReportedTotalCostStatus']
            if ((value is None and status not in ('missing_or_malformed', 'field_relationship_unverified', 'layout_unverified'))
                    or (value is not None and (status != 'source_fields_agree'
                        or money(row['RawTextbox38']) != value or money(row['RawTextbox16']) != value))):
                raise ProcessingError('readiness_reported_cost_contract_rejected')


def _sum(values):
    known = [v for v in values if v is not None]
    return (sum(known, Decimal(0)) if known else None), len(values) - len(known)


def _financial_check(rows, summary):
    # Recompute export-contract controls, never change or allocate financial values.
    known, missing = _sum([r['ReportedTotalCost'] for r in rows])
    if (any(summary[k] != rows[0][k] for k in PROVENANCE if k != 'ReportType')
            or summary['RetainedRepairCount'] != len(rows)
            or summary['SourceRecordCount'] is None or summary['SourceRecordCount'] < len(rows)
            or summary['UnavailableRepairCostCount'] != missing
            or summary['KnownRepairTotalCost'] != known):
        raise ProcessingError('readiness_financial_summary_inconsistent')
    reported = [summary[c] for c in ('ReportedLaborCost', 'ReportedPartsCost', 'ReportedTotalCost')]
    count = summary['ReportedRepairCount']
    if (count is None and any(v is not None for v in reported)) or (count is not None and
            (count != summary['SourceRecordCount'] or any(v is None for v in reported))):
        raise ProcessingError('readiness_financial_summary_inconsistent')
    complete = missing == 0 and len(rows) == summary['SourceRecordCount']
    difference = known - reported[2] if complete and reported[2] is not None else None
    components = reported[0] + reported[1] - reported[2] if all(v is not None for v in reported) else None
    state = ('source_summary_unavailable' if count is None else
             'incomplete_repair_costs_or_excluded_records' if not complete else
             'difference' if difference != 0 or components != 0 else 'arithmetic_match')
    if (summary['RepairTotalDifference'] != difference or summary['SummaryComponentsDifference'] != components
            or summary['ReconciliationStatus'] != state):
        raise ProcessingError('readiness_financial_summary_inconsistent')
    return state


def _read_csv(path, columns):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != columns:
            raise ProcessingError('readiness_input_schema_rejected')
        rows = list(reader)
        if any(None in r or any(v is None for v in r.values()) for r in rows):
            raise ProcessingError('readiness_input_row_width_rejected')
        return rows


def _expectations(path, controls):
    required = {(r['period'], r['report_type'], r['metric']) for r in controls if r['required']}
    values = {}
    if path is not None:
        for row in _read_csv(path, EXPECTATION_COLUMNS):
            key = tuple(row[k] for k in ('period', 'report_type', 'metric'))
            try:
                number = Decimal(row['expected']) if row['expected'] else None
                tolerance = Decimal(row['tolerance'])
                if (key not in required or key in values or not tolerance.is_finite() or tolerance < 0
                        or (number is not None and (not number.is_finite() or not row['evidence'].strip()))):
                    raise ValueError
            except (InvalidOperation, ValueError):
                raise ProcessingError('readiness_expectations_rejected') from None
            values[key] = (number, tolerance, row['evidence'])
    comparisons = []
    for row in controls:
        if not row['required']:
            continue
        key = row['period'], row['report_type'], row['metric']
        expected, tolerance, evidence = values.get(key, (None, Decimal(0), ''))
        status = ('not_supplied' if expected is None else 'missing_values' if row['missing_values'] else
                  'arithmetic_match' if abs(row['value'] - expected) <= tolerance else 'difference')
        comparisons.append(dict(period=key[0], report_type=key[1], metric=key[2], observed=row['value'],
            missing_values=row['missing_values'], expected=expected, tolerance=tolerance,
            difference=None if expected is None or row['missing_values'] else row['value'] - expected,
            comparison=status, evidence=evidence))
    return comparisons


def _sources(path, periods, tables):
    indexed = {}
    if path is not None:
        for row in _read_csv(path, SOURCE_COLUMNS):
            key = row['report_type'], row['period']
            if key in indexed or key[0] not in {k.value for k in ReportType} or key[1] not in periods or not row['path'].strip():
                raise ProcessingError('readiness_source_index_rejected')
            indexed[key] = path.resolve().parent / row['path']
        if set(indexed) != {(k.value, p) for k in ReportType for p in periods}:
            raise ProcessingError('readiness_source_index_incomplete')
    result = []
    for kind, records in tables.items():
        for period in periods:
            expected = next(r['SourceFileSHA256'] for r in records if r['ReportMonth'] == period)
            source = indexed.get((kind.value, period))
            if source is not None and (not source.is_file() or sha256(source.read_bytes()).hexdigest() != expected):
                raise ProcessingError('readiness_original_source_hash_mismatch')
            result.append(dict(period=period, report_type=kind.value, source_sha256=expected,
                source_integrity='verified_against_indexed_local_bytes' if source is not None else 'raw_bytes_not_supplied'))
    return result


def assess(snapshot: Path, periods, *, expectations: Path | None = None, source_index: Path | None = None):
    periods = _periods(periods)
    data = read_snapshot(snapshot)
    if sorted(data.manifest['periods']) != periods:
        raise ProcessingError('readiness_missing_or_unexpected_periods')
    if any(r['SchemaVersion'] != '2' for r in data.tables[ReportType.REPAIRS]):
        raise ProcessingError('readiness_requires_repair_schema_v2')
    controls, files, states = [], [], []
    def add(period, kind, name, values):
        value, missing = _sum(values)
        controls.append(dict(period=period, report_type=kind, metric=name, value=value,
            missing_values=missing, required=name in REQUIRED[kind]))
    for kind, rows in data.tables.items():
        for period in periods:
            monthly = [r for r in rows if r['ReportMonth'] == period]
            _same_provenance(monthly, kind)
            _record_contract(monthly, kind)
            add(period, kind.value, 'record_count', [Decimal(len(monthly))])
            key = 'WorkOrderId' if kind == ReportType.TMA_WORK_ORDERS else 'EquipmentId'
            add(period, kind.value, 'missing_identifier_count', [Decimal(sum(not r[key] for r in monthly))])
            add(period, kind.value, 'leading_zero_identifier_count', [Decimal(sum(r[key].startswith('0') for r in monthly))])
            entry = next(e for e in data.manifest['files'] if e['report_type'] == kind.value and e['period'] == period)
            if not re.fullmatch(r'[0-9a-f]{32}', entry['revision']):
                raise ProcessingError('readiness_selected_revision_rejected')
            files.append(dict(period=period, report_type=kind.value, revision=entry['revision'], file=entry['file'],
                sha256=entry['sha256'], source_sha256=monthly[0]['SourceFileSHA256'],
                source_file_name=monthly[0]['SourceFileName'], cleaner_version=monthly[0]['CleanerVersion'],
                legacy_candidate_sha256=monthly[0]['LegacyCandidateSHA256'], rows=len(monthly),
                schema_version=monthly[0]['SchemaVersion'], export_version=monthly[0]['ExportVersion'],
                reconciliation='not_applicable'))
            if kind == ReportType.REPAIRS:
                summary = data.summaries[period]
                state = _financial_check(monthly, summary)
                states.append(state)
                files[-1]['reconciliation'] = state
                extra = next(e for e in data.manifest['financial_summaries'] if e['period'] == period)
                if extra['revision'] != entry['revision']:
                    raise ProcessingError('readiness_summary_revision_mismatch')
                files.append(dict(period=period, report_type='repair_financial_summary', revision=extra['revision'],
                    file=extra['file'], sha256=extra['sha256'], source_sha256=summary['SourceFileSHA256'],
                    source_file_name=summary['SourceFileName'], cleaner_version=summary['CleanerVersion'],
                    legacy_candidate_sha256=summary['LegacyCandidateSHA256'], rows=1,
                    schema_version='2', export_version='powerbi-v2', reconciliation=state))
                add(period, kind.value, 'reported_total_cost', [r['ReportedTotalCost'] for r in monthly])
                add(period, kind.value, 'missing_reported_cost_count', [Decimal(sum(r['ReportedTotalCost'] is None for r in monthly))])
                add(period, kind.value, 'repair_person_hours', [r['RepairPersonHours'] for r in monthly])
                add(period, kind.value, 'estimated_labor_cost', [r['EstimatedLaborCost'] for r in monthly])
                for metric, column in [('reported_repair_count', 'ReportedRepairCount'),
                        ('reported_parts_cost', 'ReportedPartsCost'), ('reported_labor_cost', 'ReportedLaborCost'),
                        ('reported_total_cost', 'ReportedTotalCost')]:
                    add(period, 'repair_financial_summary', metric, [summary[column]])
    # A missing amount stays incomplete in the combined controls, not zero-filled.
    for kind, metric in sorted({(r['report_type'], r['metric']) for r in controls}):
        selected = [r for r in controls if r['report_type'] == kind and r['metric'] == metric]
        value, _ = _sum([r['value'] for r in selected])
        controls.append(dict(period='ALL', report_type=kind, metric=metric, value=value,
            missing_values=sum(r['missing_values'] for r in selected), required=metric in REQUIRED[kind]))
    comparisons = _expectations(expectations, controls)
    sources = _sources(source_index, periods, data.tables)
    return ReviewAssessment(controls, comparisons, files, sources, dict(
        report_version=1, assessed_at_utc=datetime.now(timezone.utc).isoformat(),
        validation_status='CandidateUnverified', production_ready=False, approval_record_created=False,
        periods=periods, snapshot_manifest_sha256=data.manifest_hash, structural_checks_passed=True,
        source_bytes_verified=source_index is not None,
        reported_financials_reconcile=all(s == 'arithmetic_match' for s in states),
        expected_totals_match=all(r['comparison'] == 'arithmetic_match' for r in comparisons),
        requires_manual_power_bi_test=True))


def _write_csv(path, rows):
    with path.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def template(snapshot, periods, target):
    review = assess(snapshot, periods)
    if target.resolve().is_relative_to(snapshot.resolve()):
        raise ProcessingError('readiness_report_must_be_outside_snapshot')
    _write_csv(target, [dict(period=r['period'], report_type=r['report_type'], metric=r['metric'],
        expected='', tolerance='0', evidence='') for r in review.controls if r['required']])


def write_assessment(review, snapshot, destination):
    destination = destination.absolute()
    _unlinked(destination)
    destination = destination.resolve()
    if destination.is_relative_to(snapshot.resolve()) or candidate_location_error(destination):
        raise ProcessingError('readiness_report_requires_separate_local_folder')
    destination.mkdir(parents=True, exist_ok=False)
    try:
        for name, rows in [('controls.csv', review.controls), ('comparisons.csv', review.comparisons),
                           ('selected_files.csv', review.files), ('source_integrity.csv', review.sources)]:
            _write_csv(destination / name, rows)
        (destination / 'assessment.json').write_text(json.dumps(review.status, indent=2) + '\n', encoding='utf-8')
    except BaseException:
        shutil.rmtree(destination)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['template', 'assess'])
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--month', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True, help='New private report folder, or new template CSV')
    parser.add_argument('--expectations', type=Path)
    parser.add_argument('--sources', type=Path, help='Private CSV mapping each type/month to exact original local raw path')
    args = parser.parse_args()
    try:
        if args.command == 'template':
            if args.expectations or args.sources:
                raise ProcessingError('readiness_template_does_not_accept_observations')
            template(args.snapshot, args.month, args.output)
        else:
            review = assess(args.snapshot, args.month, expectations=args.expectations, source_index=args.sources)
            write_assessment(review, args.snapshot, args.output)
            if not (review.status['reported_financials_reconcile'] and review.status['expected_totals_match']):
                print('Review report saved; missing expectations, financial values or differences need attention. No approval or Power BI execution.')
                return 2
    except (ProcessingError, OSError, ValueError, KeyError, TypeError) as error:
        print(str(error) if isinstance(error, ProcessingError) else 'readiness_input_or_output_unavailable_or_invalid')
        return 1
    print('Offline checks complete. Candidates remain unapproved; manual Power BI testing is required.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
