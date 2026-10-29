"""Invented inputs only: monthly discovery, unchanged engine and export safety."""
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
from threading import Event

import pytest
import report_samples

from equipment_data_manager.monthly import Workspace, discover, export_review_packet, load_workspace
from equipment_data_manager.powerquery_contract import read_folder, read_table
from equipment_data_manager.processing.models import ProcessingError, ProcessingStatus as Status, ReportType
from equipment_data_manager.ui.workflow import DesktopWorkflow


@pytest.fixture
def workspace(tmp_path):
    return Workspace(tmp_path / 'raw', tmp_path / 'candidates', tmp_path / 'approved')


def populate(workspace, month=1):
    for kind, factory, ext in [(ReportType.REPAIRS, report_samples.repair_csv, 'csv'),
            (ReportType.SERVICE_ORDERS, report_samples.service_csv, 'csv'),
            (ReportType.TMA_WORK_ORDERS, report_samples.tma_xlsx, 'xlsx')]:
        folder = workspace.raw_folder / f'2026-{month:02d}' / kind.value
        folder.mkdir(parents=True)
        (folder / f'raw.{ext}').write_bytes(factory(month, 3))


def process(workspace, month=1):
    workflow = DesktopWorkflow(workspace.candidate_folder, output_format='powerbi')
    selection = discover(workspace, f'2026-{month:02d}')
    previews = workflow.preview_month(selection, lambda *args: None, Event())
    results = workflow.process(previews, {}, lambda *args: None, Event())
    assert all(item.result.status == Status.SUCCESS for item in results)
    return workflow, previews


def test_configuration_relative_paths_and_reserved_approved_folder(tmp_path):
    config = tmp_path / 'workspace.toml'
    config.write_text('raw_folder="raw"\ncandidate_folder="candidates"\napproved_folder="approved"\n')
    workspace = load_workspace(config)
    assert workspace.raw_folder == tmp_path / 'raw'
    assert not workspace.approved_folder.exists()
    assert not workspace.candidate_folder.exists()


@pytest.mark.parametrize('text', ['raw_folder="raw"',
    'raw_folder="raw"\ncandidate_folder="raw/sub"\napproved_folder="approved"',
    'raw_folder="raw"\ncandidate_folder="candidates"\napproved_folder="candidates"',
    'raw_folder=""\ncandidate_folder="candidates"\napproved_folder="approved"',
    'raw_folder="raw"\ncandidate_folder="candidates"\napproved_folder="approved"\nsecret="forbidden"'])
def test_invalid_configuration_fails_without_echoing_values(tmp_path, text):
    path = tmp_path / 'config.toml'
    path.write_text(text)
    with pytest.raises(ProcessingError, match='^invalid_workspace_configuration$'):
        load_workspace(path)


def test_missing_month_is_reported_without_creating_folders(workspace):
    selection = discover(workspace, '2026-01')
    assert len(selection.missing) == 3 and len(selection.issues) == 3
    assert 'Missing reports:' in selection.summary
    assert not workspace.raw_folder.exists()


def test_discovery_nonrecursive_and_mixed_type_preview_is_write_free(workspace):
    populate(workspace)
    folder = workspace.raw_folder / '2026-01/repairs'
    (folder / 'history').mkdir()
    (folder / 'history/old.csv').write_text('not an export')
    (folder / '~download.csv').write_text('temporary')
    (folder / 'notes.txt').write_text('ignore')
    selection = discover(workspace, '2026-01')
    assert not selection.missing and len(selection.files) == 3
    workflow = DesktopWorkflow(workspace.candidate_folder, output_format='powerbi')
    progress = []
    previews = workflow.preview_month(selection, lambda done, total: progress.append((done,total)), Event())
    assert all(entry.result.status == Status.SUCCESS for entry in previews)
    assert progress == [(1,3), (2,3), (3,3)]
    assert not workspace.candidate_folder.exists()


def test_unavailable_folder_reports_sync_as_unverified(workspace, monkeypatch):
    def unavailable(*args):
        raise PermissionError('SYNTHETIC_PRIVATE_ERROR')
    monkeypatch.setattr(Path, 'iterdir', unavailable)
    selection = discover(workspace, '2026-01')
    assert len(selection.issues) == 3
    assert all('Sync is unverified' in issue for issue in selection.issues)
    assert 'SYNTHETIC' not in selection.summary


def test_two_distinct_inputs_only_block_their_own_report_type(workspace):
    populate(workspace)
    (workspace.raw_folder / '2026-01/repairs/correction.csv').write_bytes(report_samples.repair_csv(1,4))
    workflow = DesktopWorkflow(workspace.candidate_folder, output_format='powerbi')
    entries = workflow.preview_month(discover(workspace,'2026-01'), lambda *args: None, Event())
    assert [e.result.code for e in entries if e.report_type == ReportType.REPAIRS] == ['multiple_files_same_period'] * 2
    assert all(e.result.status == Status.SUCCESS for e in entries if e.report_type != ReportType.REPAIRS)


def test_packet_current_only_originals_unchanged_and_production_rejected(workspace):
    populate(workspace)
    before = {p: sha256(p.read_bytes()).hexdigest() for p in workspace.raw_folder.rglob('*') if p.is_file()}
    workflow, previews = process(workspace)
    repeated = workflow.preview_month(discover(workspace,'2026-01'), lambda *args: None, Event())
    assert all(e.result.status == Status.SKIPPED for e in repeated)
    packet = export_review_packet(workspace, workflow.coordinator, '2026-01')
    manifest = json.loads((packet / 'packet.json').read_text())
    assert manifest['status'] == 'CandidateUnverified'
    assert manifest['production_ready'] is manifest['sync_verified'] is False
    assert len(manifest['files']) == 3
    assert not workspace.approved_folder.exists()
    for kind in ReportType:
        rows = read_folder(packet / kind.value, kind, allow_candidates=True)
        assert len(rows) == 3
        with pytest.raises(ProcessingError, match='contract_rejected'):
            read_folder(packet / kind.value, kind)
    assert before == {p: sha256(p.read_bytes()).hexdigest() for p in before}
    assert export_review_packet(workspace, workflow.coordinator, '2026-01') != packet


def test_missing_or_legacy_packet_export_cannot_publish(workspace):
    workflow = DesktopWorkflow(workspace.candidate_folder, output_format='powerbi')
    with pytest.raises(ProcessingError, match='missing_reports'):
        export_review_packet(workspace, workflow.coordinator, '2026-01')
    assert not workspace.candidate_folder.exists()
    with pytest.raises(ProcessingError, match='requires_powerbi_workspace'):
        export_review_packet(workspace, DesktopWorkflow(workspace.candidate_folder).coordinator, '2026-01')


def test_corrected_month_packet_selects_new_only_and_keeps_old_packet(workspace):
    populate(workspace)
    workflow, _ = process(workspace)
    old = export_review_packet(workspace, workflow.coordinator, '2026-01')
    path = workspace.raw_folder / '2026-01/repairs/raw.csv'
    path.write_bytes(report_samples.repair_csv(1,4))
    entries = workflow.preview_month(discover(workspace,'2026-01'), lambda *args: None, Event())
    assert entries[0].result.status == Status.NEEDS_REVIEW
    unapproved = workflow.process(entries, {}, lambda *args: None, Event())
    assert unapproved[0].result.code == 'correction_not_approved'
    approved = workflow.process(entries, {0: entries[0].result.replacement_token}, lambda *args: None, Event())
    assert approved[0].result.status == Status.SUCCESS
    new = export_review_packet(workspace, workflow.coordinator, '2026-01')
    assert len(read_folder(old / 'repairs', ReportType.REPAIRS, allow_candidates=True)) == 3
    assert len(read_folder(new / 'repairs', ReportType.REPAIRS, allow_candidates=True)) == 4
    assert len(workflow.coordinator.store.history()) == 4
    assert not workspace.approved_folder.exists()


def test_tampered_current_blocks_packet_and_failed_staging_is_removed(workspace, monkeypatch):
    populate(workspace)
    workflow, _ = process(workspace)
    real_write = Path.write_text
    def failed(path, *args, **kwargs):
        if path.name == 'packet.json':
            raise OSError('injected disk failure')
        return real_write(path, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path, 'write_text', failed)
        with pytest.raises(OSError):
            export_review_packet(workspace, workflow.coordinator, '2026-01')
    assert list((workspace.candidate_folder / 'review_packets').iterdir()) == []
    artifact = workflow.coordinator.store.history()[0].artifact.output_path
    artifact.write_bytes(b'tampered')
    with pytest.raises(ProcessingError, match='hash_mismatch'):
        export_review_packet(workspace, workflow.coordinator, '2026-01')
    assert list((workspace.candidate_folder / 'review_packets').iterdir()) == []


def test_linked_raw_and_packet_directories_cannot_escape_workspace(workspace, tmp_path, monkeypatch):
    populate(workspace)
    linked = workspace.raw_folder / '2026-01/repairs/link.csv'
    # Exercise the redirect guard on Windows without requiring symlink privileges.
    linked.write_bytes(b'ignored')
    original_is_link = Path.is_symlink
    monkeypatch.setattr(Path, 'is_symlink', lambda path: path == linked or original_is_link(path))
    assert len(discover(workspace, '2026-01').files) == 3
    workflow, _ = process(workspace)
    outside = tmp_path / 'outside'
    outside.mkdir()
    packet_parent = workspace.candidate_folder / 'review_packets'
    original_resolve = Path.resolve
    monkeypatch.setattr(Path, 'resolve', lambda path, *args, **kwargs: outside if path == packet_parent else original_resolve(path, *args, **kwargs))
    with pytest.raises(ProcessingError, match='unsafe_review_packet_folder'):
        export_review_packet(workspace, workflow.coordinator, '2026-01')
    assert list(outside.iterdir()) == []


def test_folder_combines_distinct_months_text_ids_nulls_and_ignores_history(workspace, tmp_path):
    populate(workspace)
    workflow, _ = process(workspace)
    one = export_review_packet(workspace, workflow.coordinator, '2026-01')
    populate(workspace, 2)
    process(workspace, 2)
    two = export_review_packet(workspace, workflow.coordinator, '2026-02')
    folder = tmp_path / 'query-review'; folder.mkdir()
    for packet in (one,two):
        path = next((packet / 'service_orders').glob('*.csv'))
        (folder / path.name).write_bytes(path.read_bytes())
    (folder / 'history').mkdir(); (folder / 'history/old.csv').write_text('ignored')
    rows = read_folder(folder, ReportType.SERVICE_ORDERS, allow_candidates=True)
    assert len(rows) == 6 and all(isinstance(r['EquipmentId'], str) for r in rows)
    assert all(r['EstimatedPrice'] is None for r in rows)
    first = next(folder.glob('*.csv'))
    (folder / 'duplicate.csv').write_bytes(first.read_bytes())
    with pytest.raises(ProcessingError, match='duplicate_month'):
        read_folder(folder, ReportType.SERVICE_ORDERS, allow_candidates=True)


@pytest.mark.parametrize('mutation', ['schema','date','number','status','period','width'])
def test_ingestion_rejects_incompatible_contracts(workspace, mutation):
    populate(workspace)
    workflow, _ = process(workspace)
    packet = export_review_packet(workspace, workflow.coordinator,'2026-01')
    path = next((packet / 'repairs').glob('*.csv'))
    records = list(csv.reader(StringIO(path.read_text())))
    if mutation == 'schema': records[0][0] = 'Unexpected'
    elif mutation == 'date': records[1][records[0].index('CompletedDate')] = '1/1/2026'
    elif mutation == 'number': records[1][records[0].index('RepairPersonHours')] = 'NaN'
    elif mutation == 'status': records[1][records[0].index('ValidationStatus')] = 'Approved'
    elif mutation == 'period': records[1][records[0].index('ReportMonth')] = '2026-99'
    elif mutation == 'width': records[1].append('extra')
    output = StringIO(); csv.writer(output).writerows(records)
    with pytest.raises(ProcessingError, match='contract_rejected'):
        read_table(output.getvalue().encode(), ReportType.REPAIRS, allow_candidates=True)


def test_m_example_matches_all_export_schemas_and_safe_entry_points():
    # Static M contract check, not a claim to execute the Microsoft mashup engine.
    from equipment_data_manager.processing.powerbi import schema
    query = (Path(__file__).parents[1] / 'powerquery/fnReadMonthlyFolder.pq').read_text()
    for kind in ReportType:
        spec = ', '.join('{"'+c.name+'", "'+c.data_type+'"}' for c in schema(kind))
        assert f'{kind.value} = {{{spec}}}' in query
    assert 'Folder.Contents(' in query and 'Folder.Files(' not in query
    assert 'Encoding=65001' in query and 'Duplicate reporting month' in query
    assert 'CandidateUnverified' in query and 'then false else ReviewCandidates' in query


def test_changed_source_between_monthly_preview_and_processing_fails_safely(workspace):
    populate(workspace)
    workflow = DesktopWorkflow(workspace.candidate_folder, output_format='powerbi')
    selection = discover(workspace, '2026-01')
    entries = workflow.preview_month(selection, lambda *args: None, Event())
    path = workspace.raw_folder / '2026-01/repairs/raw.csv'
    path.write_bytes(report_samples.repair_csv(1,4))
    results = workflow.process(entries, {}, lambda *args: None, Event())
    assert results[0].result.code == 'input_changed_since_preview'
    assert all(item.result.status == Status.SUCCESS for item in results[1:])
    with pytest.raises(ProcessingError, match='missing_reports'):
        export_review_packet(workspace, workflow.coordinator, '2026-01')
    assert not workspace.approved_folder.exists()
