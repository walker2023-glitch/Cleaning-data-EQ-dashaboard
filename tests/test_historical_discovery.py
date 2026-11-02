"""Invented folders/bytes only. Inventory must never write sources or candidates."""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest

from report_samples import repair_csv, service_csv, tma_xlsx
from equipment_data_manager.historical import (
    discover_history, export_inventory, filename_match, month_folder_period,
    periods_between, verify_inventory_source,
)
from equipment_data_manager.monthly import Workspace, discover
from equipment_data_manager.processing.models import ProcessingError, ReportType
from equipment_data_manager.settings import Preferences, SettingsStore, UserSettings, encode_settings, parse_settings
from equipment_data_manager.storage.contracts import StorageError
from equipment_data_manager.storage.local import LocalFolderStorage
from equipment_data_manager.ui.workflow import DesktopWorkflow


def populate(root, period='2026-01', label='Jan', layout='sharepoint_year_month', *, valid=False):
    folder = root / (f'{period[:4]}/{period} ({label})' if layout == 'sharepoint_year_month' else period)
    month = int(period[5:])
    for kind, name, data in (
        (ReportType.REPAIRS, 'CompuClean Repair Report.csv', repair_csv(month, 2) if valid else b'SYNTHETIC repairs'),
        (ReportType.SERVICE_ORDERS, 'CompuClean Service Orders List.csv', service_csv(month, 2) if valid else b'SYNTHETIC services'),
        (ReportType.TMA_WORK_ORDERS, f'Work Orders {label} {period[:4]}.xlsx', tma_xlsx(month, 2) if valid else b'SYNTHETIC TMA'),
    ):
        target = folder / kind.value if layout == 'standard' else folder
        target.mkdir(parents=True, exist_ok=True)
        (target / name).write_bytes(data)
    return folder


def scan(root, start='2026-01', end=None, **kwargs):
    return discover_history(LocalFolderStorage(root, synced=True), start, end or start,
                            kwargs.pop('layout', 'sharepoint_year_month'), **kwargs)


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('layout', ['standard', 'sharepoint_year_month'])
def test_both_layouts_hash_exact_original_bytes_without_writes(tmp_path, layout):
    root = tmp_path / 'raw'
    populate(root, layout=layout)
    before = snapshot(root)
    inventory = scan(root, layout=layout)
    assert inventory.months[0].complete and not inventory.stopped
    for report in inventory.months[0].reports:
        source, = report.sources
        assert source.sha256 == sha256((root / source.item_id).read_bytes()).hexdigest()
        assert not verify_inventory_source(LocalFolderStorage(root, synced=True), source).sync_verified
    assert snapshot(root) == before and set(tmp_path.iterdir()) == {root}
    document = inventory.document()
    assert document['processing_performed'] is False and document['approval'] == 'not_granted'
    assert document['sync_verified'] is False


@pytest.mark.parametrize('label,month', [('Jan',1),('January',1),('Feb',2),('March',3),('April',4),('Sept',9),('September',9),('sep',9),('DECEMBER',12)])
def test_abbreviated_and_full_labels(tmp_path, label, month):
    period = f'2026-{month:02d}'
    populate(tmp_path, period, label)
    assert scan(tmp_path, period).months[0].complete
    assert month_folder_period(f'{period} ({label})', '2026') == period


@pytest.mark.parametrize('name', ['2026-01 (Feb)', '2025-01 (Jan)', '2026-13 (Jan)', '2026-1 (Jan)', 'January 2026', '2026-01', '2026-01 (Unknown)'])
def test_invalid_month_folder_never_selected(tmp_path, name):
    (tmp_path / '2026' / name).mkdir(parents=True)
    month = scan(tmp_path).months[0]
    assert not month.complete and not month.folders
    assert all(not r.sources for r in month.reports)
    assert any(i.code.startswith('historical_') for i in month.issues)


def test_duplicate_month_aliases_no_arbitrary_choice(tmp_path):
    populate(tmp_path, label='Jan')
    populate(tmp_path, label='January')
    month = scan(tmp_path).months[0]
    assert len(month.folders) == 2 and not month.complete
    assert all(r.status == 'ambiguous' and not r.sources for r in month.reports)


def test_multiyear_range_missing_month_and_report_preserve_all_slots(tmp_path):
    populate(tmp_path, '2025-12', 'Dec')
    folder = populate(tmp_path, '2026-02', 'February')
    (folder / 'CompuClean Service Orders List.csv').unlink()
    inventory = scan(tmp_path, '2025-12', '2026-02')
    assert [m.period for m in inventory.months] == ['2025-12','2026-01','2026-02']
    assert inventory.months[0].complete
    assert all(r.status == 'missing' for r in inventory.months[1].reports)
    assert inventory.months[2].reports[1].status == 'missing'


@pytest.mark.parametrize('start,end', [('2026-02','2026-01'), ('2026-13','2026-13'), ('2026-1','2026-01'), ('2010-01','2026-01')])
def test_invalid_and_unbounded_ranges_rejected(start, end):
    with pytest.raises(ProcessingError):
        periods_between(start, end)


@pytest.mark.parametrize('name,kind,issue', [
    ('CompuClean_Repair_Report.CSV', ReportType.REPAIRS, ''),
    ('CompuClean-Service-Orders-List.csv', ReportType.SERVICE_ORDERS, ''),
    ('Work Orders January 2026.xlsx', ReportType.TMA_WORK_ORDERS, ''),
    ('Work Orders February 2026.xlsx', ReportType.TMA_WORK_ORDERS, 'historical_filename_month_mismatch'),
    ('Repair Report.csv', None, 'historical_unrecognized_filename'),
    ('CompuClean Repair Report copy.csv', None, 'historical_unrecognized_filename'),
    ('anything.xlsx', None, 'historical_unrecognized_filename'),
])
def test_anchored_filename_routing(name, kind, issue):
    assert filename_match(name, '2026-01') == (kind, issue)


def test_duplicate_supported_names_never_selected_even_identical_content(tmp_path):
    folder = populate(tmp_path)
    (folder / 'CompuClean_Repair_Report.csv').write_bytes((folder / 'CompuClean Repair Report.csv').read_bytes())
    report = scan(tmp_path).months[0].reports[0]
    assert report.status == 'ambiguous' and len(report.sources) == 2
    assert any(i.code == 'historical_duplicate_reports' for i in report.issues)


@pytest.mark.parametrize('name,code', [('Work Orders Jan 2026.xls','historical_legacy_xls_unsupported'),
    ('Work Orders Jan 2026.csv','historical_unsupported_extension'),
    ('Work Orders Feb 2026.xlsx','historical_filename_month_mismatch')])
def test_unsupported_or_wrong_month_reports_blocked(tmp_path, name, code):
    folder = populate(tmp_path)
    (folder / 'Work Orders Jan 2026.xlsx').rename(folder / name)
    report = scan(tmp_path).months[0].reports[2]
    assert report.status == 'blocked' and any(i.code == code for i in report.issues)


def test_temporary_unknown_and_history_sources_not_ingested(tmp_path):
    folder = populate(tmp_path)
    for name in ('~$Work Orders Jan 2026.xlsx', 'CompuClean Repair Report.csv.part', 'unrelated.csv'):
        (folder / name).write_bytes(b'SYNTHETIC not selected')
    (folder / 'history').mkdir()
    (folder / 'history/CompuClean Repair Report.csv').write_bytes(b'old synthetic')
    month = scan(tmp_path).months[0]
    assert not month.complete and len(month.issues) == 3
    assert all(len(r.sources) == 1 for r in month.reports)
    assert not any('history' in s.item_id for r in month.reports for s in r.sources)


def test_standard_layout_keeps_arbitrary_filename_routing(tmp_path):
    folder = populate(tmp_path, layout='standard')
    (folder / 'repairs/CompuClean Repair Report.csv').rename(folder / 'repairs/arbitrary.csv')
    assert scan(tmp_path, layout='standard').months[0].complete


def test_provider_availability_failures_are_explicit_and_private_messages_redacted(tmp_path, monkeypatch):
    populate(tmp_path)
    def fail(self, source, **kwargs):
        raise StorageError('storage_file_not_downloaded')
    monkeypatch.setattr(LocalFolderStorage, 'read', fail)
    month = scan(tmp_path).months[0]
    assert not month.complete
    assert all(r.status == 'blocked' and r.sources[0].sha256 is None for r in month.reports)
    assert all(r.issues[0].code == 'storage_file_not_downloaded' for r in month.reports)


def test_change_between_discovery_and_preview_is_rejected(tmp_path):
    populate(tmp_path, valid=True)
    inventory = scan(tmp_path)
    source = inventory.months[0].reports[0].sources[0]
    (tmp_path / source.item_id).write_bytes(b'changed synthetic source')
    with pytest.raises(StorageError, match='source_changed'):
        verify_inventory_source(LocalFolderStorage(tmp_path, synced=True), source)


def test_missing_root_and_access_denied_are_not_empty_success(tmp_path, monkeypatch):
    result = scan(tmp_path / 'missing')
    assert not result.months[0].complete and result.months[0].issues[0].code == 'storage_folder_missing'
    def denied(self, folder):
        raise StorageError('storage_access_denied')
    monkeypatch.setattr(LocalFolderStorage, 'list_folders', denied)
    assert scan(tmp_path).months[0].issues[0].code == 'storage_access_denied'


def test_links_never_followed_or_historical_files_ingested(tmp_path):
    from unittest.mock import patch
    folder = populate(tmp_path)
    # Mock Windows junction classification to test this guard on both CI platforms.
    original = Path.is_junction
    with patch.object(Path, 'is_junction', lambda p: True if p == folder else original(p)):
        month = scan(tmp_path).months[0]
    assert not month.complete and any(i.code == 'storage_link_rejected' for i in month.issues)


def test_cancelled_inventory_keeps_unscanned_months_and_never_processes(tmp_path):
    populate(tmp_path)
    stop = Event()
    calls = []
    def progress(done, total):
        calls.append((done, total))
        stop.set()
    result = scan(tmp_path, '2026-01', '2026-03', cancelled=stop, progress=progress)
    assert result.stopped and len(result.months) == 3 and result.months[0].complete
    assert all(r.status == 'not_scanned' for m in result.months[1:] for r in m.reports)
    assert calls[-1] == (3,3) and not list(tmp_path.rglob('*.sqlite3'))


def test_stop_between_files_does_not_label_partial_month_complete(tmp_path, monkeypatch):
    populate(tmp_path)
    stop = Event()
    original = LocalFolderStorage.read
    def read(self, source, **kwargs):
        value = original(self, source, **kwargs)
        stop.set()
        return value
    monkeypatch.setattr(LocalFolderStorage, 'read', read)
    result = scan(tmp_path, cancelled=stop)
    assert result.stopped and not result.months[0].complete
    assert any(i.code == 'historical_scan_stopped' for i in result.months[0].issues)


def test_export_is_local_exclusive_no_raw_writes_and_no_approval(tmp_path):
    raw = tmp_path / 'raw'
    populate(raw)
    inventory = scan(raw)
    target = tmp_path / 'inventory.json'
    export_inventory(inventory, target)
    data = json.loads(target.read_text())
    assert data['inventory_only'] and not data['processing_performed'] and not data['sync_verified']
    with pytest.raises(StorageError, match='historical_export_exists'):
        export_inventory(inventory, target)
    with pytest.raises(StorageError, match='overlaps_raw'):
        export_inventory(inventory, raw / 'inventory.json')
    with pytest.raises(StorageError):
        export_inventory(inventory, tmp_path / 'OneDrive/private.json')
    assert not (raw / 'inventory.json').exists()


def test_settings_additive_layout_roundtrip_and_old_versions_default(tmp_path):
    settings = UserSettings(preferences=Preferences(reporting_period='2026-01', folder_layout='sharepoint_year_month'))
    store = SettingsStore(tmp_path / 'settings.toml')
    store.save(settings)
    assert store.load() == settings
    old = '\n'.join(line for line in encode_settings(settings).splitlines() if not line.startswith('folder_layout ='))
    assert parse_settings(old, base=tmp_path).preferences.folder_layout == 'standard'
    with pytest.raises(ProcessingError, match='settings_invalid'):
        parse_settings(encode_settings(settings).replace('sharepoint_year_month', '../escape'), base=tmp_path)


def test_sharepoint_month_uses_real_engine_and_discovery_hash_guard(tmp_path):
    raw = tmp_path / 'raw'
    populate(raw, valid=True)
    workspace = Workspace(raw, tmp_path / 'candidates', tmp_path / 'approved')
    selection = discover(workspace, '2026-01', folder_layout='sharepoint_year_month')
    assert not selection.missing and not selection.issues
    before = snapshot(raw)
    workflow = DesktopWorkflow(workspace.candidate_folder, output_format='powerbi')
    preview = workflow.preview_month(selection, lambda *a: None, Event())
    assert all(p.result.status == 'success' for p in preview) and not workspace.candidate_folder.exists()
    result = workflow.process(preview, {}, lambda *a: None, Event())
    assert all(r.result.status == 'success' for r in result)
    again = workflow.preview_month(selection, lambda *a: None, Event())
    assert all(p.result.status == 'skipped' for p in again)
    repair, = [p for p in result if p.preview.report_type == ReportType.REPAIRS]
    assert 'ReportedTotalCost' in repair.result.output_location.read_text()
    assert snapshot(raw) == before and not workspace.approved_folder.exists()
    source = selection.files[0][1]
    Path(source.reference).write_bytes(b'changed synthetic data')
    stale = workflow.preview_month(selection, lambda *a: None, Event())
    assert stale[0].result.status == 'failure'


def test_inventory_does_not_claim_schema_support_or_preview_old_layout(tmp_path):
    raw = tmp_path / 'raw'
    populate(raw, valid=False)
    assert scan(raw).months[0].complete  # Only filename/readability completeness.
    selection = discover(Workspace(raw, tmp_path / 'out', tmp_path / 'approved'), '2026-01', folder_layout='sharepoint_year_month')
    preview = DesktopWorkflow(tmp_path / 'out', output_format='powerbi').preview_month(selection, lambda *a: None, Event())
    assert all(p.result.status == 'failure' for p in preview)
    assert not (tmp_path / 'out').exists()


def test_placeholder_folder_fails_before_enumeration(tmp_path, monkeypatch):
    import equipment_data_manager.storage.local as local
    provider = LocalFolderStorage(tmp_path)
    original = Path.stat
    info = original(tmp_path)
    values = {key:getattr(info,key) for key in ('st_mode','st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns')}
    values['st_file_attributes'] = 0x400000
    monkeypatch.setattr(Path,'stat', lambda path,*a,**kw: SimpleNamespace(**values) if path == tmp_path else original(path,*a,**kw))
    def forbidden(*a,**kw):
        raise AssertionError('must not enumerate cloud-only folder')
    monkeypatch.setattr(local.os, 'scandir', forbidden)
    with pytest.raises(StorageError,match='storage_file_not_downloaded'):
        provider.list_folders('.')


def test_oversized_source_is_flagged_before_reading_bytes(tmp_path, monkeypatch):
    import equipment_data_manager.historical as historical
    populate(tmp_path)
    monkeypatch.setattr(historical,'MAX_FILE_BYTES',1)
    def forbidden(*a,**kw):
        raise AssertionError('oversized sources must not be read')
    monkeypatch.setattr(LocalFolderStorage,'read',forbidden)
    month = scan(tmp_path).months[0]
    assert all(r.status == 'blocked' and r.issues[0].code == 'historical_file_too_large' for r in month.reports)


def test_directory_entry_cap_does_not_recurse(tmp_path, monkeypatch):
    import equipment_data_manager.storage.local as local
    class Entries:
        def __enter__(self):
            entry = SimpleNamespace(path=str(tmp_path / 'entry'), name='entry', is_dir=lambda **kw:False)
            return iter([entry] * 4097)
        def __exit__(self,*args):
            pass
    monkeypatch.setattr(local.os,'scandir',lambda folder:Entries())
    with pytest.raises(StorageError,match='storage_directory_limit'):
        LocalFolderStorage(tmp_path).list_folders('.')


def test_snapshot_and_reconciliation_stay_separate_and_financial_v2_is_preserved(tmp_path):
    # Reuse the established four-table snapshot + independent-control tooling.
    # No historical-discovery function assembles or approves it automatically.
    import importlib.util
    location = Path(__file__).resolve().parents[1] / 'examples/create_powerbi_pilot.py'
    spec = importlib.util.spec_from_file_location('historical_snapshot_regression', location)
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    root = tmp_path / 'existing-pilot'
    demo.create_demo(root, financial_v2=True, complete_financial=True)
    from equipment_data_manager.powerbi_pilot import read_snapshot
    data = read_snapshot(root / 'pilot/snapshot')
    assert data.manifest['periods'] == ['2026-01','2026-02']
    assert data.manifest['status'] == 'CandidateUnverified' and data.manifest['production_ready'] is False
    assert len(data.manifest['financial_summaries']) == 2
    assert {entry['period'] for entry in data.manifest['financial_summaries']} == {'2026-01','2026-02'}
    assert (root / 'reconciliation.csv').is_file()
    before = snapshot(root / 'candidates')
    inventory = scan(root / 'raw', '2026-01','2026-02',layout='standard')
    assert all(month.complete for month in inventory.months)
    assert snapshot(root / 'candidates') == before
    assert not (root / 'reserved-approved').exists()
