"""Synthetic local/synced availability checks; no cloud SDK or sync assertion."""
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from threading import Event

import pytest
from report_samples import service_csv
from equipment_data_manager.storage.contracts import StorageError
from equipment_data_manager.storage.local import LocalFolderStorage, read_local_file, UNAVAILABLE_ATTRIBUTES
from equipment_data_manager.storage.discovery import discover_reports
from equipment_data_manager.storage.source import ProviderFileSource
from equipment_data_manager.processing.models import ReportType
from equipment_data_manager.ui.workflow import DesktopWorkflow, SourceFile


def test_local_and_synced_provider_read_same_original_bytes_without_claiming_sync(tmp_path):
    folder=tmp_path/'2026-01/service_orders';folder.mkdir(parents=True)
    path=folder/'raw.csv';raw=service_csv(1,3);path.write_bytes(raw)
    for synced in (False,True):
        provider=LocalFolderStorage(tmp_path,synced=synced)
        entry,=provider.list_files('2026-01/service_orders')
        read=provider.read(entry,expected_sha256=sha256(raw).hexdigest())
        assert read.content==raw and not read.sync_verified
        assert 'sync_unverified' in read.integrity
        assert 'Synthetic' not in repr(read) and 'raw.csv' not in repr(entry)
        assert path.read_bytes()==raw


@pytest.mark.parametrize('flag',[0x1000,0x40000,0x400000])
def test_windows_offline_or_recall_files_are_not_opened_merely_because_they_exist(tmp_path,monkeypatch,flag):
    path=tmp_path/'placeholder.csv';path.write_bytes(b'synthetic')
    info=path.stat();real_stat=Path.stat;real_open=Path.open
    values={k:getattr(info,k) for k in ['st_mode','st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns']}
    values['st_file_attributes']=flag
    monkeypatch.setattr(Path,'stat',lambda p,*a,**kw:SimpleNamespace(**values) if p==path else real_stat(p,*a,**kw))
    def guarded(p,*a,**kw):
        if p==path:raise AssertionError('must not trigger automatic hydration')
        return real_open(p,*a,**kw)
    monkeypatch.setattr(Path,'open',guarded)
    with pytest.raises(StorageError,match='not_downloaded'):read_local_file(path)


def test_partial_bytes_and_changed_source_during_read_are_rejected(tmp_path,monkeypatch):
    path=tmp_path/'partial.csv';path.write_bytes(b'complete-original')
    original=Path.open
    monkeypatch.setattr(Path,'open',lambda p,*a,**kw:BytesIO(b'part') if p==path else original(p,*a,**kw))
    with pytest.raises(StorageError,match='changed_or_partial'):read_local_file(path)
    monkeypatch.setattr(Path,'open',original)
    provider=LocalFolderStorage(tmp_path);entry,=provider.list_files('.')
    path.write_bytes(b'changed-new-report')
    with pytest.raises(StorageError,match='source_changed'):provider.read(entry)


def test_missing_denied_and_wrong_hash_have_safe_categories(tmp_path,monkeypatch):
    with pytest.raises(StorageError,match='input_not_a_file'):read_local_file(tmp_path/'missing')
    path=tmp_path/'raw.csv';path.write_bytes(b'synthetic')
    with pytest.raises(StorageError,match='hash_mismatch'):read_local_file(path,expected_sha256='0'*64)
    original=Path.open
    def denied(p,*a,**kw):
        if p==path:raise PermissionError('PRIVATE MESSAGE')
        return original(p,*a,**kw)
    monkeypatch.setattr(Path,'open',denied)
    with pytest.raises(StorageError) as error:read_local_file(path)
    assert str(error.value)=='storage_access_denied' and 'PRIVATE' not in str(error.value)


def test_no_recursive_history_ingestion_or_path_escape_and_basename_is_not_identity(tmp_path):
    for folder in ('2026-01/repairs','2026-01/service_orders','2026-01/tma_work_orders'):
        path=tmp_path/folder;path.mkdir(parents=True)
        (path/'same.csv').write_bytes(b'synthetic')
        (path/'history').mkdir();(path/'history/old.csv').write_bytes(b'ignore')
        (path/'~partial.csv').write_bytes(b'ignore')
    (tmp_path/'2026-01/tma_work_orders/raw.xlsx').write_bytes(b'synthetic')
    provider=LocalFolderStorage(tmp_path)
    selection=discover_reports(provider,'2026-01',{k:f'2026-01/{k.value}' for k in ReportType})
    assert len(selection.files)==3 and not selection.missing
    assert selection.files[0][1].name==selection.files[1][1].name
    assert selection.files[0][1].item_id!=selection.files[1][1].item_id
    with pytest.raises(StorageError):provider.list_files('../outside')
    with pytest.raises(StorageError):discover_reports(provider,'2026-01',{})
    missing=discover_reports(provider,'2026-02',{k:f'2026-02/{k.value}' for k in ReportType})
    assert len(missing.missing)==3 and len(missing.issues)==3


def test_provider_bridge_uses_real_cleaning_and_keeps_sqlite_local(tmp_path):
    raw=tmp_path/'synced-raw';folder=raw/'month';folder.mkdir(parents=True)
    path=folder/'service.csv';source=service_csv(1,3);path.write_bytes(source)
    provider=LocalFolderStorage(raw,synced=True);entry,=provider.list_files('month')
    bridge=ProviderFileSource(provider,{'selected':entry})
    workflow=DesktopWorkflow(tmp_path/'local-output',source=bridge,output_format='powerbi')
    preview=workflow.preview([SourceFile('selected',entry.name)],ReportType.SERVICE_ORDERS,'2026-01',lambda *a:None,Event())
    assert preview[0].result.status=='success' and not (tmp_path/'local-output').exists()
    result=workflow.process(preview,{},lambda *a:None,Event())[0].result
    assert result.status=='success' and result.output_rows==3
    assert not list(raw.rglob('*.sqlite3')) and path.read_bytes()==source
    assert workflow.coordinator.store.root.is_relative_to(tmp_path/'local-output')
    with pytest.raises(StorageError):bridge.read(SourceFile('selected','different.csv'))
    with pytest.raises(StorageError):provider.read(replace(entry,container='different-root'))
