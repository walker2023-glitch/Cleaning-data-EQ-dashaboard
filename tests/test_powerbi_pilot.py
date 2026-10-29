"""Synthetic end-to-end pilot, snapshot isolation and reconciliation regressions."""
import csv
from decimal import Decimal
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from equipment_data_manager.powerbi_pilot import (
    assemble, baseline_template, reconcile, validate_snapshot,
)
from equipment_data_manager.processing.models import ProcessingError, ReportType
from equipment_data_manager.processing.powerbi import schema

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples/create_powerbi_pilot.py'
spec = importlib.util.spec_from_file_location('pilot_demo', EXAMPLE)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


@pytest.fixture
def pilot(tmp_path):
    root = tmp_path / 'demo'
    snapshot = demo.create_demo(root)
    return root, snapshot


def packets(root):
    return sorted((root / 'candidates/review_packets').iterdir())


def edit_baseline(root, change):
    path = root / 'synthetic-baselines.csv'
    with path.open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        names, rows = reader.fieldnames, list(reader)
    change(rows)
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_real_engine_two_month_contract_and_no_approval(pilot):
    root, snapshot = pilot
    tables = validate_snapshot(snapshot)
    assert {kind: len(rows) for kind, rows in tables.items()} == {kind: 4 for kind in ReportType}
    assert tables[ReportType.REPAIRS][0]['EquipmentId'] == '000438'
    assert tables[ReportType.TMA_WORK_ORDERS][0]['WorkOrderId'] == '000128'
    assert str(tables[ReportType.REPAIRS][0]['CompletedDate']) == '2026-01-15'
    assert tables[ReportType.REPAIRS][0]['RepairPersonHours'] == Decimal('2')
    assert all(r['EstimatedPrice'] is None for r in tables[ReportType.SERVICE_ORDERS])
    assert all(r['ValidationStatus'] == 'CandidateUnverified' for rows in tables.values() for r in rows)
    assert not (root / 'reserved-approved').exists()
    assert not list((snapshot / 'tables').rglob('*.sqlite3'))
    # Historical candidate revisions live outside the selected tables.
    assert list((root / 'candidates/powerbi_candidates/versions').iterdir())
    assert len(list((snapshot / 'tables').rglob('*.csv'))) == 6
    assert (root / 'reconciliation.csv').read_text() == (EXAMPLE.parent / 'powerbi_pilot_reconciliation.csv').read_text()


def test_source_bytes_are_unchanged_and_old_snapshots_not_replaced(pilot, tmp_path):
    root, snapshot = pilot
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    with pytest.raises(FileExistsError):
        assemble(packets(root), ['2026-01', '2026-02'], root / 'pilot')
    assert before == {p: p.read_bytes() for p in before}
    new = assemble(packets(root), ['2026-01', '2026-02'], tmp_path / 'second')
    assert validate_snapshot(new) == validate_snapshot(snapshot)


@pytest.mark.parametrize('selection,months,code', [
    ([0], ['2026-01', '2026-02'], 'pilot_missing_month'),
    ([0, 0], ['2026-01', '2026-02'], 'pilot_duplicate_or_unexpected_packet_month'),
    ([0, 1], ['2026-01'], 'pilot_duplicate_or_unexpected_packet_month'),
    ([0, 1], ['2026-01', '2026-01'], 'pilot_empty_or_duplicate_month_selection'),
])
def test_packet_selection_fails_without_output(pilot, tmp_path, selection, months, code):
    root, _ = pilot
    destination = tmp_path / 'rejected'
    with pytest.raises(ProcessingError, match=code):
        assemble([packets(root)[i] for i in selection], months, destination)
    assert not destination.exists()


@pytest.mark.parametrize('change,code', [
    (lambda m: m['files'].pop(), 'pilot_missing_report_type'),
    (lambda m: m['files'][0].update(file='../escape.csv'), 'pilot_packet_path_or_period_rejected'),
    (lambda m: m['files'][0].update(sha256='0'*64), 'pilot_packet_hash_mismatch'),
    (lambda m: m['files'][0].update(rows=500), 'pilot_packet_count_or_period_mismatch'),
    (lambda m: m.update(status='Approved'), 'pilot_candidate_packet_required'),
])
def test_packet_integrity_rejected(pilot, tmp_path, change, code):
    root, _ = pilot
    manifest = packets(root)[0] / 'packet.json'
    data = json.loads(manifest.read_text())
    change(data)
    manifest.write_text(json.dumps(data))
    with pytest.raises(ProcessingError, match=code):
        assemble(packets(root), ['2026-01', '2026-02'], tmp_path / 'rejected')
    assert not (tmp_path / 'rejected').exists()


@pytest.mark.parametrize('operation', ['delete', 'duplicate', 'history', 'schema', 'tamper'])
def test_snapshot_detects_missing_duplicate_historical_schema_and_changed_files(pilot, operation):
    _, snapshot = pilot
    path = next((snapshot / 'tables/repairs').glob('*.csv'))
    if operation == 'delete':
        path.unlink()
    elif operation == 'duplicate':
        path.with_name('second.csv').write_bytes(path.read_bytes())
    elif operation == 'history':
        (path.parent / 'versions').mkdir()
    else:
        path.write_bytes(path.read_bytes().replace(b'EquipmentId', b'UnknownId') if operation == 'schema'
                         else path.read_bytes() + b'\n')
        if operation == 'schema':
            manifest = snapshot / 'snapshot.json'
            data = json.loads(manifest.read_text())
            for e in data['files']:
                if e['file'] == f'repairs/{path.name}':
                    e['sha256'] = sha256(path.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(data))
    with pytest.raises(ProcessingError):
        validate_snapshot(snapshot)


def test_failed_staging_leaves_no_partial_snapshot(pilot, tmp_path, monkeypatch):
    root, _ = pilot
    import equipment_data_manager.powerbi_pilot as module
    monkeypatch.setattr(module, 'validate_snapshot', lambda *_: (_ for _ in ()).throw(OSError('disk error')))
    with pytest.raises(OSError):
        assemble(packets(root), ['2026-01', '2026-02'], tmp_path / 'failed')
    assert not (tmp_path / 'failed').exists()


def test_reconciliation_distinguishes_unknowns_nulls_differences_and_blockers(pilot):
    root, snapshot = pilot
    report = reconcile(snapshot, root / 'synthetic-baselines.csv')
    lookup = {(r['report_type'], r['period'], r['metric']): r for r in report}
    jan = lookup['repairs', '2026-01', 'parts_cost']
    assert Decimal(jan['cleaned_known_sum']) == 20
    assert jan['source_total'] == '30'  # NOT repeated-summary 60
    assert Decimal(jan['source_delta']) == -10
    assert jan['source_comparison'] == 'business_mapping_unconfirmed'
    feb = lookup['repairs', '2026-02', 'parts_cost']
    assert feb['missing_values'] == 1
    assert feb['source_comparison'] == 'incomplete_cleaned_values'
    assert feb['source_delta'] == ''  # Never compare a partial sum as a total.
    assert lookup['repairs', '2026-01', 'rows']['powerbi_comparison'] == 'arithmetic_match'
    assert lookup['repairs', '2026-01', 'hours']['source_comparison'] == 'not_supplied'
    assert lookup['service_orders', '2026-01', 'service_price']['cleaned_known_sum'] == ''
    assert all(r['validation_status'] == 'CandidateUnverified' for r in report)
    baseline = edit_baseline(root, lambda rows: rows[0].update(powerbi_total='5', tolerance='1'))
    assert reconcile(snapshot, baseline)[0]['powerbi_comparison'] == 'difference'
    baseline = edit_baseline(root, lambda rows: rows[0].update(tolerance='3'))
    assert reconcile(snapshot, baseline)[0]['powerbi_comparison'] == 'arithmetic_match'


def test_empty_baseline_is_pending_and_template_refuses_overwrite(pilot):
    root, snapshot = pilot
    path = root / 'empty.csv'
    baseline_template(snapshot, path)
    result = reconcile(snapshot, path)
    assert all(r['source_total'] == r['powerbi_total'] == '' for r in result)
    assert all(r['source_comparison'] == r['powerbi_comparison'] == 'not_supplied' for r in result)
    with pytest.raises(FileExistsError):
        baseline_template(snapshot, path)
    with pytest.raises(ProcessingError, match='inside_ingestion'):
        baseline_template(snapshot, snapshot / 'tables/repairs/report.csv')


@pytest.mark.parametrize('changes', [dict(tolerance='-1'), dict(tolerance='NaN'),
    dict(source_total='Infinity'), dict(comparable='yes'), dict(metric='invented'),
    dict(period='2026-03'), dict(evidence=''), dict(powerbi_measure='')])
def test_invalid_baseline_rejected(pilot, changes):
    root, snapshot = pilot
    baseline = edit_baseline(root, lambda rows: rows[0].update(changes))
    with pytest.raises(ProcessingError, match='pilot_baseline_values_rejected'):
        reconcile(snapshot, baseline)


def test_duplicate_baseline_rejected(pilot):
    root, snapshot = pilot
    baseline = edit_baseline(root, lambda rows: rows.append(rows[0]))
    with pytest.raises(ProcessingError, match='pilot_baseline_values_rejected'):
        reconcile(snapshot, baseline)


def test_cli_check_and_report_location(pilot):
    root, snapshot = pilot
    command = [sys.executable, '-m', 'equipment_data_manager.powerbi_pilot']
    result = subprocess.run([*command, 'check', str(snapshot)], capture_output=True, text=True)
    assert result.returncode == 0 and 'No approval' in result.stdout
    result = subprocess.run([*command, 'reconcile', str(snapshot), '--baseline', str(root / 'synthetic-baselines.csv'),
        '--output', str(snapshot / 'tables/repairs/bad.csv')], capture_output=True, text=True)
    assert result.returncode == 1 and 'inside_ingestion' in result.stderr
    assert not (snapshot / 'tables/repairs/bad.csv').exists()


def test_m_examples_have_explicit_candidate_mode_completeness_and_schema_types():
    root = EXAMPLE.parents[1]
    function = (root / 'powerquery/fnReadMonthlyFolder.pq').read_text()
    assert 'optional ExpectedMonths as nullable list' in function
    assert 'List.Sort(Months) = List.Sort(Expected)' in function
    assert 'Folder.Contents(' in function and 'Folder.Files(' not in function
    for kind in ReportType:
        for column in schema(kind):
            assert '{"' + column.name + '", "' + column.data_type + '"}' in function
    for file in ('PilotRepairs.pq', 'PilotServiceOrders.pq', 'PilotTmaWorkOrders.pq'):
        assert 'true, {"2026-01", "2026-02"}' in (root / 'powerquery' / file).read_text()


def test_corrected_month_requires_engine_review_and_new_pinned_snapshot(pilot, tmp_path):
    from equipment_data_manager.monthly import Workspace, export_review_packet
    from equipment_data_manager.processing.models import ProcessingRequest
    from equipment_data_manager.processing.powerbi import powerbi_coordinator
    root, old = pilot
    old_bytes = {p: p.read_bytes() for p in old.rglob('*') if p.is_file()}
    workspace = Workspace(root / 'raw', root / 'candidates', root / 'reserved-approved')
    engine = powerbi_coordinator(workspace.candidate_folder)
    original = root / 'raw/2026-01/repairs/synthetic.csv'
    source = original.read_bytes()
    corrected = source.replace(b'Synthetic repair', b'Synthetic corrected repair')
    request = ProcessingRequest('repairs', '2026-01', raw_bytes=corrected, source_name='correction.csv')
    pending = engine.process(request)
    assert pending.status == 'needs_review'
    confirmed = engine.process(ProcessingRequest('repairs', '2026-01', raw_bytes=corrected,
        source_name='correction.csv', replacement_token=pending.replacement_token))
    assert confirmed.status == 'success'
    corrected_packet = export_review_packet(workspace, engine, '2026-01')
    feb = next(p for p in packets(root) if json.loads((p / 'packet.json').read_text())['period'] == '2026-02')
    new = assemble([corrected_packet, feb], ['2026-01', '2026-02'], tmp_path / 'corrected')
    assert original.read_bytes() == source
    assert old_bytes == {p: p.read_bytes() for p in old_bytes}
    old_rows = validate_snapshot(old)[ReportType.REPAIRS]
    new_rows = validate_snapshot(new)[ReportType.REPAIRS]
    assert old_rows[0]['SourceFileSHA256'] != new_rows[0]['SourceFileSHA256']
    assert len(new_rows) == 4  # No extra January history rows.


def test_linked_input_is_rejected_without_destination(pilot, tmp_path, monkeypatch):
    root, _ = pilot
    selected = packets(root)
    monkeypatch.setattr(Path, 'is_junction', lambda path: path == selected[0])
    with pytest.raises(ProcessingError, match='pilot_link_rejected'):
        assemble(selected, ['2026-01', '2026-02'], tmp_path / 'linked')
    assert not (tmp_path / 'linked').exists()


def test_m_control_metrics_match_python_comparison_contract():
    from equipment_data_manager.powerbi_pilot import METRICS
    text = (EXAMPLE.parents[1] / 'powerquery/fnMonthlyControlTotals.pq').read_text()
    for metrics in METRICS.values():
        for metric, column in metrics.items():
            assert '{"' + metric + '", ' + ('null' if column is None else '"' + column + '"') + '}' in text
    assert 'List.RemoveNulls(Values)' in text
    assert 'missing_values=List.Count(Values)-List.Count(Known)' in text


def test_network_or_known_synced_snapshot_destination_is_rejected(pilot, tmp_path, monkeypatch):
    import equipment_data_manager.powerbi_pilot as module
    root, _ = pilot
    monkeypatch.setattr(module, 'candidate_location_error', lambda _: 'Known synced path')
    with pytest.raises(ProcessingError, match='trusted_local_unsynced'):
        assemble(packets(root), ['2026-01', '2026-02'], tmp_path / 'synced')
    assert not (tmp_path / 'synced').exists()
