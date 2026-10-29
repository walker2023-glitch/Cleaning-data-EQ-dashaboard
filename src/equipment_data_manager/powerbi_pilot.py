"""Explicit, candidate-only multi-month snapshots and offline reconciliation.

No recursive discovery, approval, publishing, Power BI connection or cleaning logic.
Use a trusted local disk and a single operator; snapshots are immutable by procedure.
"""

import argparse
import csv
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
import shutil

from equipment_data_manager.powerquery_contract import read_table
from equipment_data_manager.processing.cleaners import validate_period
from equipment_data_manager.processing.manifest import OUTPUT_NAMES
from equipment_data_manager.processing.models import ProcessingError, ReportType
from equipment_data_manager.settings import candidate_location_error

# Metrics are comparison views of existing columns, never new cleaning calculations.
METRICS = {
    ReportType.REPAIRS: {'rows': None, 'repair_count': 'RepairCount', 'hours': 'RepairPersonHours',
        'parts_cost': 'PartsCost', 'labor_cost': 'LaborCost', 'estimated_total': 'EstimatedTotalCost',
        'legacy_parts_cost': 'LegacyPartsCost', 'legacy_estimated_total': 'LegacyEstimatedTotalCost'},
    ReportType.SERVICE_ORDERS: {'rows': None, 'service_price': 'EstimatedPrice'},
    ReportType.TMA_WORK_ORDERS: {'rows': None},
}
REPAIR_V2_METRICS = {'rows': None, 'repair_count': 'RepairCount', 'hours': 'RepairPersonHours',
    'reported_total_cost': 'ReportedTotalCost', 'estimated_labor_cost': 'EstimatedLaborCost',
    'legacy_parts_cost': 'LegacyPartsCost', 'legacy_labor_cost': 'LegacyLaborCost',
    'legacy_estimated_total': 'LegacyEstimatedTotalCost'}


def _metrics(kind, records):
    return REPAIR_V2_METRICS if kind == ReportType.REPAIRS and 'ReportedTotalCost' in records[0] else METRICS[kind]


BASELINE_COLUMNS = ['report_type', 'period', 'metric', 'source_total', 'powerbi_total',
                    'powerbi_measure', 'tolerance', 'comparable', 'evidence']


def _periods(periods):
    if not periods or len(set(periods)) != len(periods):
        raise ProcessingError('pilot_empty_or_duplicate_month_selection')
    for period in periods:
        validate_period(period)
    return sorted(periods)


def _unlinked(path):
    if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise ProcessingError('pilot_link_rejected')


def assemble(packet_paths: list[Path], periods: list[str], destination: Path, *, require_repair_v2=False) -> Path:
    """Select exactly one explicit complete review packet/month; fail before writes.

    Creates a new exclusive destination containing snapshot/. Existing folders are
    never reused or overwritten. Source bytes and all historical revisions stay put.
    """
    periods = _periods(periods)
    payloads, selected, summaries, seen = [], [], [], set()
    for packet in packet_paths:
        _unlinked(packet.absolute())
        data = json.loads((packet / 'packet.json').read_text(encoding='utf-8'))
        period = data['period']
        if period not in periods or period in seen:
            raise ProcessingError('pilot_duplicate_or_unexpected_packet_month')
        if data['status'] != 'CandidateUnverified' or data['production_ready'] is not False:
            raise ProcessingError('pilot_candidate_packet_required')
        entries = data['files']
        if len(entries) != len(ReportType) or {e['report_type'] for e in entries} != {k.value for k in ReportType}:
            raise ProcessingError('pilot_missing_report_type')
        for entry in entries:
            kind = ReportType(entry['report_type'])
            relative = f'{kind.value}/{OUTPUT_NAMES[kind]}_{period}.csv'
            if entry['file'] != relative or entry['period'] != period:
                raise ProcessingError('pilot_packet_path_or_period_rejected')
            path = packet / relative
            _unlinked(path.absolute())
            raw = path.read_bytes()
            if sha256(raw).hexdigest() != entry['sha256']:
                raise ProcessingError('pilot_packet_hash_mismatch')
            rows = read_table(raw, kind, allow_candidates=True)
            if len(rows) != entry['rows'] or rows[0]['ReportMonth'] != period:
                raise ProcessingError('pilot_packet_count_or_period_mismatch')
            payloads.append((relative, raw))
            selected.append(dict(entry))
        extra = data.get('supplemental_files', [])
        repair_raw = next(raw for name, raw in payloads if name == f'repairs/{OUTPUT_NAMES[ReportType.REPAIRS]}_{period}.csv')
        repair_rows = read_table(repair_raw, ReportType.REPAIRS, allow_candidates=True)
        if require_repair_v2 and repair_rows[0]['SchemaVersion'] != '2':
            raise ProcessingError('readiness_requires_repair_schema_v2')
        _summary_payload(packet, repair_rows, extra, payloads, summaries)
        seen.add(period)
    if seen != set(periods):
        raise ProcessingError('pilot_missing_month')
    destination = destination.absolute()
    _unlinked(destination)
    destination = destination.resolve()
    if candidate_location_error(destination):
        raise ProcessingError('pilot_requires_trusted_local_unsynced_destination')
    if any(destination.is_relative_to(p.resolve()) or p.resolve().is_relative_to(destination)
           for p in packet_paths):
        raise ProcessingError('pilot_destination_overlaps_packets')
    # Exclusive ownership of this new directory prevents races/overwrites.
    destination.mkdir(parents=True, exist_ok=False)
    stage = destination / '.staging'
    try:
        stage.mkdir()
        for relative, raw in payloads:
            target = stage / 'tables' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        (stage / 'snapshot.json').write_text(json.dumps(dict(
            status='CandidateUnverified', production_ready=False, periods=periods, files=selected, financial_summaries=summaries),
            indent=2) + '\n', encoding='utf-8')
        validate_snapshot(stage)
        stage.rename(destination / 'snapshot')
    except BaseException:
        shutil.rmtree(destination)
        raise
    return destination / 'snapshot'


@dataclass(repr=False)
class SnapshotData:
    tables: dict = field(repr=False)
    summaries: dict = field(repr=False)
    manifest: dict = field(repr=False)
    manifest_hash: str


def validate_snapshot(root: Path):
    """Backward-compatible table view of a fully hash-checked snapshot."""
    return read_snapshot(root).tables


def read_snapshot(root: Path):
    """Parse the SAME bytes whose hashes were checked, once per artifact."""
    _unlinked(root.absolute())
    if candidate_location_error(root.absolute()):
        raise ProcessingError('pilot_requires_trusted_local_unsynced_destination')
    manifest_raw = (root / 'snapshot.json').read_bytes()
    manifest = json.loads(manifest_raw.decode('utf-8'))
    periods = _periods(manifest['periods'])
    if manifest['status'] != 'CandidateUnverified' or manifest['production_ready'] is not False:
        raise ProcessingError('pilot_candidate_snapshot_required')
    entries = manifest['files']
    expected = {(kind.value, period) for kind in ReportType for period in periods}
    if len(entries) != len(expected) or {(e['report_type'], e['period']) for e in entries} != expected:
        raise ProcessingError('pilot_incomplete_manifest')
    all_rows, financial_rows = {}, {}
    tables = root / 'tables'
    summaries = manifest.get('financial_summaries', [])
    expected_folders = {k.value for k in ReportType} | ({'repair_financial_summary'} if summaries else set())
    if {p.name for p in tables.iterdir()} != expected_folders:
        raise ProcessingError('pilot_unexpected_table_folder')
    for kind in ReportType:
        chosen = [e for e in entries if e['report_type'] == kind.value]
        names = {f'{OUTPUT_NAMES[kind]}_{e["period"]}.csv' for e in chosen}
        folder = tables / kind.value
        _unlinked(folder.absolute())
        if {p.name for p in folder.iterdir()} != names:
            raise ProcessingError('pilot_missing_or_extra_files')
        records, versions, identifiers = [], set(), set()
        for entry in chosen:
            name = f'{OUTPUT_NAMES[kind]}_{entry["period"]}.csv'
            if entry['file'] != f'{kind.value}/{name}':
                raise ProcessingError('pilot_manifest_path_rejected')
            path = folder / name
            _unlinked(path.absolute())
            raw = path.read_bytes()
            if sha256(raw).hexdigest() != entry['sha256']:
                raise ProcessingError('pilot_snapshot_hash_mismatch')
            rows = read_table(raw, kind, allow_candidates=True)
            if rows[0]['ReportMonth'] != entry['period'] or len(rows) != entry['rows']:
                raise ProcessingError('pilot_snapshot_count_or_period_mismatch')
            versions.add(rows[0]['SchemaVersion'])
            if len(versions) > 1:
                raise ProcessingError('folder_ingestion_mixed_schema_versions')
            if any(r['RecordId'] in identifiers for r in rows):
                raise ProcessingError('folder_ingestion_duplicate_month_or_record')
            identifiers.update(r['RecordId'] for r in rows)
            records.extend(rows)
        rows = records
        if {r['ReportMonth'] for r in rows} != set(periods):
            raise ProcessingError('pilot_missing_month')
        all_rows[kind] = rows
    repairs = all_rows[ReportType.REPAIRS]
    for period in periods:
        monthly = [r for r in repairs if r['ReportMonth'] == period]
        extra = [e for e in summaries if e['period'] == period]
        summary = _summary_payload(tables, monthly, extra, [], [])
        if summary is not None:
            financial_rows[period] = summary
    if summaries:
        folder = tables / 'repair_financial_summary'
        _unlinked(folder.absolute())
        if len(summaries) != len(periods) or {p.name for p in folder.iterdir()} != {Path(e['file']).name for e in summaries}:
            raise ProcessingError('pilot_missing_or_extra_financial_summaries')
    return SnapshotData(all_rows, financial_rows, manifest, sha256(manifest_raw).hexdigest())


def _summary_payload(parent, repair_rows, entries, payloads, manifests):
    from equipment_data_manager.processing.repair_financial import read_summary, summary_name
    v2 = repair_rows[0]['SchemaVersion'] == '2'
    if not v2:
        if entries:
            raise ProcessingError('pilot_unexpected_financial_summary')
        return
    period = repair_rows[0]['ReportMonth']
    relative = 'repair_financial_summary/' + summary_name(period)
    if (len(entries) != 1 or entries[0]['file'] != relative or entries[0]['period'] != period
            or entries[0].get('report_type') != 'repair_financial_summary' or entries[0].get('rows') != 1):
        raise ProcessingError('pilot_missing_or_extra_financial_summaries')
    path = parent / relative
    _unlinked(path.absolute())
    raw = path.read_bytes()
    digest = sha256(raw).hexdigest()
    if entries[0]['sha256'] != digest or any(r['FinancialSummarySHA256'] != digest for r in repair_rows):
        raise ProcessingError('pilot_financial_summary_hash_mismatch')
    summary = read_summary(raw)
    if summary['ReportMonth'] != period or summary['SourceFileSHA256'] != repair_rows[0]['SourceFileSHA256']:
        raise ProcessingError('pilot_financial_summary_provenance_mismatch')
    payloads.append((relative, raw))
    manifests.extend(entries)
    return summary


def baseline_template(root: Path, target: Path):
    """Blank observations are unknown, never zero or inferred dashboard totals."""
    rows = validate_snapshot(root)
    if target.resolve().is_relative_to((root / 'tables').resolve()):
        raise ProcessingError('pilot_report_inside_ingestion_folder')
    with target.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=BASELINE_COLUMNS)
        writer.writeheader()
        for kind, records in rows.items():
            for period in sorted({r['ReportMonth'] for r in records}):
                for metric in _metrics(kind, records):
                    writer.writerow(dict(report_type=kind.value, period=period, metric=metric,
                                         tolerance='0', comparable='false'))


def _number(value):
    if value == '':
        return None
    number = Decimal(value)
    if not number.is_finite():
        raise ValueError('Nonfinite comparison')
    return number


def reconcile(root: Path, baseline: Path):
    """One complete grid, explicit source/PBI observations, deltas and unknowns.

    Arithmetic agreement is not approval. Incomplete sums never compare as totals.
    """
    tables = validate_snapshot(root)
    observations = {}
    with baseline.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != BASELINE_COLUMNS:
            raise ProcessingError('pilot_baseline_schema_rejected')
        for row in reader:
            try:
                kind = ReportType(row['report_type'])
                key = (kind, row['period'], row['metric'])
                if (None in row or any(v is None for v in row.values()) or key in observations
                        or row['metric'] not in _metrics(kind, tables[kind])
                        or row['period'] not in {r['ReportMonth'] for r in tables[kind]}
                        or row['comparable'] not in ('true', 'false')):
                    raise ValueError
                source, pbi, tolerance = (_number(row[k]) for k in ('source_total', 'powerbi_total', 'tolerance'))
                if tolerance is None or tolerance < 0:
                    raise ValueError
                if (source is not None or pbi is not None or row['comparable'] == 'true') and not row['evidence'].strip():
                    raise ValueError
                if pbi is not None and not row['powerbi_measure'].strip():
                    raise ValueError
                observations[key] = (row, source, pbi, tolerance)
            except (ValueError, InvalidOperation, KeyError, TypeError):
                raise ProcessingError('pilot_baseline_values_rejected') from None
    report = []
    for kind, rows in tables.items():
        for period in sorted({r['ReportMonth'] for r in rows}):
            monthly = [r for r in rows if r['ReportMonth'] == period]
            for metric, column in _metrics(kind, rows).items():
                observed, source, pbi, tolerance = observations.get((kind, period, metric), ({}, None, None, Decimal(0)))
                values = [r[column] for r in monthly] if column else [Decimal(1) for _ in monthly]
                nonnull = [v for v in values if v is not None]
                total = sum(nonnull, Decimal(0)) if nonnull else None
                missing = len(values) - len(nonnull)
                comparable = observed.get('comparable') == 'true'
                def comparison(value):
                    if value is None:
                        return 'not_supplied'
                    if missing:
                        return 'incomplete_cleaned_values'
                    if not comparable:
                        return 'business_mapping_unconfirmed'
                    return 'arithmetic_match' if abs(total - value) <= tolerance else 'difference'
                report.append(dict(report_type=kind.value, period=period, metric=metric,
                    cleaned_known_sum='' if total is None else str(total), missing_values=missing,
                    source_total='' if source is None else str(source),
                    source_delta='' if source is None or total is None or missing else str(total - source),
                    source_comparison=comparison(source), powerbi_total='' if pbi is None else str(pbi),
                    powerbi_delta='' if pbi is None or total is None or missing else str(total - pbi),
                    powerbi_comparison=comparison(pbi), powerbi_measure=observed.get('powerbi_measure', ''),
                    tolerance=str(tolerance), evidence=observed.get('evidence', ''),
                    validation_status='CandidateUnverified'))
    return report


def write_report(rows, target):
    with target.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('assemble', help='Select explicit monthly candidate packets; never scan history')
    build.add_argument('--require-repair-v2', action='store_true', help='Reject legacy repair packets before writing a new snapshot')
    build.add_argument('--packet', action='append', type=Path, required=True)
    build.add_argument('--month', action='append', required=True)
    build.add_argument('--output', type=Path, required=True, help='NEW local directory; existing directories rejected')
    check = commands.add_parser('check')
    check.add_argument('snapshot', type=Path)
    template = commands.add_parser('baseline-template')
    template.add_argument('snapshot', type=Path)
    template.add_argument('--output', type=Path, required=True)
    compare = commands.add_parser('reconcile')
    compare.add_argument('snapshot', type=Path)
    compare.add_argument('--baseline', type=Path, required=True)
    compare.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'assemble':
            assemble(args.packet, args.month, args.output, require_repair_v2=args.require_repair_v2)
        elif args.command == 'check':
            validate_snapshot(args.snapshot)
        elif args.command == 'baseline-template':
            baseline_template(args.snapshot, args.output)
        else:
            # Reports must live outside the ingestion tables tree.
            if args.output.resolve().is_relative_to((args.snapshot / 'tables').resolve()):
                raise ProcessingError('pilot_report_inside_ingestion_folder')
            write_report(reconcile(args.snapshot, args.baseline), args.output)
    except FileExistsError:
        parser.exit(1, 'pilot_output_exists_use_a_new_destination_or_report_name\n')
    except FileNotFoundError:
        parser.exit(1, 'pilot_file_missing_check_selection_and_local_availability\n')
    except PermissionError:
        parser.exit(1, 'pilot_access_denied_check_local_folder_permissions\n')
    except (ProcessingError, OSError, ValueError, KeyError, TypeError) as error:
        code = str(error) if isinstance(error, ProcessingError) else 'pilot_invalid_or_unavailable_input_or_output'
        parser.exit(1, code + '\n')
    print('Offline candidate pilot complete. No approval, Power BI refresh or publication occurred.')


if __name__ == '__main__':
    main()
