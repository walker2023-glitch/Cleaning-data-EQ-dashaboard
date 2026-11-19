"""Development comparison projections of validated historical snapshots.

No cleaner, candidate store, activation, Power BI or network operation is called.
The exact canonical input is retained privately under audit/canonical. Public CSVs
are projections, not a replacement for the historical-powerbi-v1 contract.
"""

import argparse
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import shutil

from equipment_data_manager.historical_dataset import (
    NAMES as CANONICAL_NAMES, _encode, _safe, _write, validate_dataset,
)
from equipment_data_manager.monthly import Workspace, _check_windows_packet_paths
from equipment_data_manager.processing.models import ProcessingError, ReportType
from equipment_data_manager.processing.powerbi import schema as transaction_schema
from equipment_data_manager.processing.repair_financial import (
    BUSINESS as REPAIR_FIELDS, SUMMARY_COLUMNS, schema as repair_schema,
)
from equipment_data_manager.processing.interfaces import ColumnSchema
from equipment_data_manager.settings import candidate_location_error


EXPORT_SCHEMA = 'comparison-preview-v1'
NAMES = dict(CANONICAL_NAMES)  # Independent projection registry; canonical stays four-table.
# One ordered registry governs projection, validation and the import contract.
# Later enrichment belongs here/in project_tables, under a new contract version;
# never add derived fields to the canonical cleaner or historical snapshot schema.
FIELDS = {
    'repairs': ('ReportMonth',) + tuple(c for c in REPAIR_FIELDS if c not in {
        'LegacyRowNumber', 'RawTextbox38', 'RawTextbox16', 'FinancialSummarySHA256'}),
    'service_orders': ('ReportMonth', 'EquipmentId', 'EquipmentName', 'ScheduledDate',
        'CompletedDate', 'Location', 'Description', 'Status', 'RawStatus', 'EstimatedPrice',
        'RawDescription', 'SourceMaintenanceTag', 'AccountName', 'SourceVendorName',
        'RawCost', 'RawEquipmentId'),
    'tma_work_orders': ('ReportMonth', 'WorkOrderId', 'RequestDate', 'Requestor', 'Request', 'AssignedTo'),
    'repair_financial_summary': SUMMARY_COLUMNS[:12] + (
        'EstimatedLaborCostSum', 'EstimatedLaborCostMissingCount',
        'LegacyPartsCostSum', 'LegacyPartsCostMissingCount',
        'LegacyLaborCostSum', 'LegacyLaborCostMissingCount',
        'LegacyEstimatedTotalCostSum', 'LegacyEstimatedTotalCostMissingCount'),
}
LINEAGE_FIELDS = ('Dataset', 'ExportRecordNumber', 'CanonicalRecordNumber', 'RecordId',
    'ReportMonth', 'CandidateRevisionId', 'CandidateOutputSHA256', 'CandidateCleanerVersion',
    'SourceFileName', 'SourceFileSHA256', 'SourceRecordNumber', 'FinancialSummarySHA256')
CANONICAL_FILES = (*CANONICAL_NAMES.values(), 'snapshot_manifest.json', 'compatibility_report.md')
MANIFEST_NAME = 'comparison_manifest.json'
LINEAGE_NAME = 'audit/lineage.csv'


def schema(kind):
    """Explicit types for this projection; identifiers always remain text."""
    if kind == 'repair_financial_summary':
        integers = {'ReportedRepairCount', 'SourceRecordCount', 'RetainedRepairCount',
                    'UnavailableRepairCostCount'}
        texts = {'ReportMonth', 'ReconciliationStatus'}
        return tuple(ColumnSchema(n, 'text' if n in texts else 'integer'
            if n in integers or n.endswith('MissingCount') else 'decimal') for n in FIELDS[kind])
    base = repair_schema() if kind == 'repairs' else transaction_schema(ReportType(kind))
    types = {c.name: c.data_type for c in base}
    return tuple(ColumnSchema(n, types[n]) for n in FIELDS[kind])


def _json(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode('utf-8')


def _rows(raw):
    return list(csv.DictReader(StringIO(raw.decode('utf-8-sig'), newline=''), strict=True))


def _capture(snapshot):
    """Capture only canonical allowlisted files; hash the same bytes we project.

    Validation precedes capture; every captured CSV/report is checked against the
    captured manifest. The retained copy is validated again before completion.
    No assumption that an external process leaves the source directory unchanged.
    """
    snapshot = _safe(snapshot, local=True)
    manifest = validate_dataset(snapshot)
    payloads = {name: _safe(snapshot / name).read_bytes() for name in CANONICAL_FILES}
    if json.loads(payloads['snapshot_manifest.json']) != manifest:
        raise ProcessingError('comparison_source_changed')
    for entry in manifest['datasets']:
        if sha256(payloads[entry['file']]).hexdigest() != entry['sha256']:
            raise ProcessingError('comparison_source_changed')
    if sha256(payloads['compatibility_report.md']).hexdigest() != manifest['compatibility_report_sha256']:
        raise ProcessingError('comparison_source_changed')
    return manifest, payloads


def project_tables(payloads):
    """Pure, ordered projection. Never parse/reformat financial strings or dedupe."""
    tables, lineage = {}, []
    for kind, fields in FIELDS.items():
        records = _rows(payloads[NAMES[kind]])
        # Validate the projected contract too, including summary controls that are
        # additional to the canonical monthly summary reader. Never reserialize
        # parsed values: canonical decimal/date strings remain byte-for-byte cells.
        for row in records:
            for column in schema(kind):
                value = row[column.name]
                try:
                    if not value or column.data_type == 'text':
                        continue
                    if column.data_type == 'date':
                        if date.fromisoformat(value).isoformat() != value:
                            raise ValueError
                    else:
                        number = Decimal(value)
                        if not number.is_finite() or (column.data_type == 'integer' and number != number.to_integral_value()):
                            raise ValueError
                except (ValueError, InvalidOperation):
                    raise ProcessingError('comparison_invalid_value') from None
        tables[kind] = _encode([{field: row[field] for field in fields} for row in records], fields)
        for ordinal, row in enumerate(records, 1):
            evidence = {key: row.get(key, '') for key in LINEAGE_FIELDS}
            evidence.update(Dataset=NAMES[kind], ExportRecordNumber=ordinal, CanonicalRecordNumber=ordinal)
            lineage.append(evidence)
    return tables, _encode(lineage, LINEAGE_FIELDS)


def _manifest(source, payloads, tables, lineage):
    entries = []
    for kind, raw in tables.items():
        records = _rows(raw)
        entries.append(dict(report_type=kind, file=NAMES[kind], rows=len(records),
            rows_by_month={m: sum(r['ReportMonth'] == m for r in records)
                for m in sorted({r['ReportMonth'] for r in records})},
            columns=[dict(name=c.name, type=c.data_type) for c in schema(kind)],
            sha256=sha256(raw).hexdigest()))
    return dict(export_schema=EXPORT_SCHEMA, purpose='DevelopmentComparison',
        status='CandidateUnverified', approval_status='NotApproved', production_ready=False,
        source_snapshot_schema=source['snapshot_schema'], start=source['start'], end=source['end'],
        source_manifest_sha256=sha256(payloads['snapshot_manifest.json']).hexdigest(),
        datasets=entries, lineage=dict(file=LINEAGE_NAME, columns=list(LINEAGE_FIELDS),
            rows=sum(e['rows'] for e in entries), sha256=sha256(lineage).hexdigest()))


def _destination(workspace, source, destination, *, windows=None):
    import sys
    workspace.validate()
    source, final = _safe(source, local=True), _safe(destination, local=True)
    if candidate_location_error(final):
        raise ProcessingError('comparison_local_required')
    for protected in (source, workspace.raw_folder, workspace.candidate_folder, workspace.approved_folder):
        protected = Path(protected).resolve()
        if final.resolve().is_relative_to(protected) or protected.is_relative_to(final.resolve()):
            raise ProcessingError('comparison_destination_overlap')
    stage, completed = final / '.s', final / 'comparison'
    if windows if windows is not None else sys.platform == 'win32':
        relatives = (*NAMES.values(), MANIFEST_NAME, LINEAGE_NAME,
            *(f'audit/canonical/{name}' for name in CANONICAL_FILES))
        _check_windows_packet_paths(stage, completed, relatives)
    return final, stage, completed


def generate_comparison(workspace, snapshot, destination, *, confirmed=False,
                        progress=lambda *_: None, cancelled=lambda: False):
    """Create a new immutable comparison container after explicit local-test intent.

    The caller supplies the configured protected workspace roots. A completed
    snapshot and its internal copy never consult raw files or current candidates.
    """
    if confirmed is not True:
        raise ProcessingError('comparison_confirmation_required')
    final, stage, completed = _destination(workspace, snapshot, destination)
    if final.exists():
        raise ProcessingError('comparison_destination_exists')
    if cancelled():
        raise ProcessingError('comparison_cancelled')
    source, payloads = _capture(snapshot)
    tables, lineage = project_tables(payloads)
    manifest = _manifest(source, payloads, tables, lineage)
    if cancelled():
        raise ProcessingError('comparison_cancelled')
    _destination(workspace, snapshot, destination)
    final.parent.mkdir(parents=True, exist_ok=True)
    final.mkdir(exist_ok=False)  # Cleanup starts only after exclusive ownership.
    try:
        (stage / 'audit/canonical').mkdir(parents=True)
        outputs = {NAMES[k]: raw for k, raw in tables.items()}
        outputs.update({f'audit/canonical/{name}': raw for name, raw in payloads.items()})
        outputs[LINEAGE_NAME] = lineage
        outputs[MANIFEST_NAME] = _json(manifest)
        for index, (name, raw) in enumerate(outputs.items(), 1):
            if cancelled():
                raise ProcessingError('comparison_cancelled')
            _write(stage / name, raw)
            progress(index, len(outputs))
        validate_comparison(stage)
        if cancelled():
            raise ProcessingError('comparison_cancelled')
        stage.rename(completed)
    except BaseException:
        shutil.rmtree(final)
        raise
    return completed


def validate_comparison(root):
    """Verify projections AND complete lineage against the retained canonical copy.

    Hashes describe integrity, not a signature or authoritative business approval.
    No paths supplied in an untrusted manifest are followed.
    """
    try:
        root = _safe(root, local=True)
        if {p.name for p in root.iterdir()} != {*NAMES.values(), MANIFEST_NAME, 'audit'}:
            raise ProcessingError('comparison_contract_rejected')
        audit = _safe(root / 'audit')
        if {p.name for p in audit.iterdir()} != {'canonical', 'lineage.csv'}:
            raise ProcessingError('comparison_contract_rejected')
        source, payloads = _capture(audit / 'canonical')
        tables, lineage = project_tables(payloads)
        manifest = json.loads(_safe(root / MANIFEST_NAME).read_bytes())
        if manifest != _manifest(source, payloads, tables, lineage):
            raise ProcessingError('comparison_contract_rejected')
        for kind, raw in tables.items():
            if _safe(root / NAMES[kind]).read_bytes() != raw:
                raise ProcessingError('comparison_projection_mismatch')
        if _safe(root / LINEAGE_NAME).read_bytes() != lineage:
            raise ProcessingError('comparison_lineage_mismatch')
        return manifest
    except ProcessingError:
        raise
    except (OSError, ValueError, KeyError, TypeError, csv.Error):
        raise ProcessingError('comparison_contract_rejected') from None


def main(argv=None):
    parser = argparse.ArgumentParser(description='Development comparison only; no activation, cleaning or Power BI changes')
    parser.add_argument('--verify', type=Path)
    parser.add_argument('--snapshot', type=Path)
    parser.add_argument('--destination', type=Path)
    for name in ('raw-folder', 'candidate-folder', 'approved-folder'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--confirm-local-test', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.verify:
            validate_comparison(args.verify)
            print('Comparison integrity passed. Development comparison only; not approved.')
        else:
            if any(getattr(args, name) is None for name in (
                'snapshot', 'destination', 'raw_folder', 'candidate_folder', 'approved_folder')):
                parser.error('Supply snapshot, destination and three protected workspace folders, or --verify')
            workspace = Workspace(args.raw_folder, args.candidate_folder, args.approved_folder)
            result = generate_comparison(workspace, args.snapshot, args.destination, confirmed=args.confirm_local_test)
            print('Development comparison created:', result)
    except (ProcessingError, OSError):
        parser.exit(1, 'Comparison stopped. Check snapshot integrity, trusted local paths and explicit test confirmation.\n')


if __name__ == '__main__':
    main()
