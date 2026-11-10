"""Windows policy/race simulations; portable tests also run natively in CI."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PureWindowsPath
from threading import Barrier
from types import SimpleNamespace

import pytest

from test_historical_preview import setup, run
from test_review_requests import reviewing
from equipment_data_manager.historical_preview import export_preview
from equipment_data_manager.processing.models import ProcessingError
from equipment_data_manager.review import ReviewService


def windows_policy(monkeypatch):
    import equipment_data_manager.settings as settings
    monkeypatch.setattr(settings,'sys',SimpleNamespace(platform='win32'))
    monkeypatch.setattr(settings,'known_sync_roots',lambda:[])
    monkeypatch.setattr(settings.ctypes,'windll',SimpleNamespace(kernel32=SimpleNamespace(GetDriveTypeW=lambda _:3)),raising=False)


@pytest.mark.parametrize('method',['is_symlink','is_junction'])
@pytest.mark.parametrize('suffix',['.csv','.exe'])
def test_windows_link_rejection_precedes_other_validation_and_never_writes(tmp_path,monkeypatch,method,suffix):
    root=tmp_path/'raw';setup(root)
    batch=run(root,tmp_path/'out')
    windows_policy(monkeypatch)
    original=getattr(Path,method)
    monkeypatch.setattr(Path,method,lambda path:path==tmp_path or original(path))
    target=tmp_path/('diagnostic'+suffix)
    opened=Path.open
    def no_target_open(path,*args,**kwargs):
        assert path!=target, 'Linked destination must never be opened'
        return opened(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',no_target_open)
    with pytest.raises(ProcessingError,match='^storage_path_rejected$'):
        export_preview(batch,target,protected_roots=(root,))
    assert not target.exists() and not (tmp_path/'out').exists()


def test_review_does_not_compare_independently_resolved_sqlite_and_root_aliases(reviewing,monkeypatch):
    _,_,service=reviewing
    root=service.root
    database=root/'requests.sqlite3'
    original=Path.resolve
    calls=[]
    def aliases(path,*args,**kwargs):
        if path==database:
            calls.append('database')
            # Simulate a previously nonexistent child resolved using a short alias.
            return PureWindowsPath('C:/SHORT~1/review_requests/requests.sqlite3')
        if path==root:
            return PureWindowsPath('C:/Synthetic Long Temp/review_requests')
        return original(path,*args,**kwargs)
    import equipment_data_manager.review as module
    # Location policy is tested separately; this reproduces the second _path guard.
    monkeypatch.setattr(module,'candidate_location_error',lambda _: '')
    monkeypatch.setattr(Path,'resolve',aliases)
    assert service._path()==database
    assert calls==[]


def test_parallel_independent_services_share_one_append_only_record(reviewing):
    workspace,engine,service=reviewing
    fingerprint=service.capture('2026-01')['fingerprint']
    start=Barrier(4)
    def request(_):
        separate=ReviewService(engine,raw_folder=workspace.raw_folder)
        start.wait(timeout=10)
        return separate.request('2026-01',fingerprint,'Same simultaneous synthetic evidence')
    with ThreadPoolExecutor(max_workers=4) as pool:
        records=list(pool.map(request,range(4)))
    assert all(record==records[0] for record in records)
    assert service.history()==[records[0]]


@pytest.mark.parametrize('suffix',['.exe','.txt',''])
def test_invalid_export_extension_rejected_before_location_policy(tmp_path,monkeypatch,suffix):
    root=tmp_path/'raw';setup(root)
    batch=run(root,tmp_path/'out')
    import equipment_data_manager.historical_preview as module
    def policy(_):pytest.fail('Invalid extension must fail before location lookup')
    monkeypatch.setattr(module,'candidate_location_error',policy)
    target=tmp_path/('diagnostic'+suffix)
    with pytest.raises(ProcessingError,match='^historical_export_requires_local_csv_or_json$'):
        export_preview(batch,target,protected_roots=(root,))
    assert not target.exists()


@pytest.mark.parametrize('attributes',[0x400,0x40000,0x400000])
def test_review_reparse_and_cloud_nodes_fail_closed_with_safe_notes(reviewing,monkeypatch,attributes):
    _,_,service=reviewing
    service.root.mkdir()
    original=Path.lstat
    def flagged(path,*args,**kwargs):
        value=original(path,*args,**kwargs)
        if path==service.root:
            return SimpleNamespace(st_mode=value.st_mode,st_file_attributes=attributes)
        return value
    monkeypatch.setattr(Path,'lstat',flagged)
    with pytest.raises(ProcessingError,match=r'^review_store_unsafe\b') as caught:
        service._path()
    notes=' '.join(caught.value.__notes__)
    assert 'redirected_or_cloud_node' in notes and str(attributes) in notes
    assert str(service.root) not in notes and not (service.root/'requests.sqlite3').exists()


@pytest.mark.parametrize('attributes',[0x10,0x30,0x110,0x2010])
def test_normal_windows_directory_attributes_do_not_become_reparse_flags(reviewing,monkeypatch,attributes):
    _,_,service=reviewing
    service.root.mkdir()
    original=Path.lstat
    def ordinary(path,*args,**kwargs):
        value=original(path,*args,**kwargs)
        return SimpleNamespace(st_mode=value.st_mode,st_file_attributes=attributes) if path==service.root else value
    monkeypatch.setattr(Path,'lstat',ordinary)
    assert service._path()==service.root/'requests.sqlite3'


def test_review_metadata_error_fails_closed_instead_of_being_ignored(reviewing,monkeypatch):
    _,_,service=reviewing
    original=Path.lstat
    def unavailable(path,*args,**kwargs):
        if path==service.root:
            error=OSError('SYNTHETIC PRIVATE PATH MUST NOT APPEAR')
            error.winerror=32
            raise error
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'lstat',unavailable)
    with pytest.raises(ProcessingError,match=r'^review_store_unsafe\b') as caught:
        service._path()
    assert 'metadata_unavailable' in str(caught.value.__notes__) and '32' in str(caught.value.__notes__)
    assert 'PRIVATE' not in str(caught.value.__notes__)


def test_real_redirected_review_directory_is_rejected_without_writing(reviewing,tmp_path):
    import subprocess
    import sys
    _,_,service=reviewing
    outside=tmp_path/'redirect-target';outside.mkdir()
    if sys.platform=='win32':
        subprocess.run(['cmd','/c','mklink','/J',str(service.root),str(outside)],check=True,capture_output=True)
        assert service.root.is_junction()
    else:
        service.root.symlink_to(outside,target_is_directory=True)
        assert service.root.is_symlink()
    fingerprint=service.capture('2026-01')['fingerprint']
    with pytest.raises(ProcessingError,match=r'^review_store_unsafe\b'):
        service.request('2026-01',fingerprint,'Synthetic evidence')
    assert list(outside.iterdir())==[]
    with pytest.raises(ProcessingError,match=r'^review_store_unsafe\b'):
        service.history()


def test_database_child_must_be_an_ordinary_file(reviewing):
    _,_,service=reviewing
    database=service.root/'requests.sqlite3'
    database.mkdir(parents=True)
    with pytest.raises(ProcessingError,match=r'^review_store_unsafe\b') as caught:
        service._path()
    assert 'unexpected_node_type' in str(caught.value.__notes__)


def test_directory_is_rechecked_after_creation_before_database_open(reviewing,monkeypatch):
    _,_,service=reviewing
    fingerprint=service.capture('2026-01')['fingerprint']
    original=Path.mkdir
    created=False
    original_check=service._path
    def changed_after_mkdir(path,*args,**kwargs):
        nonlocal created
        result=original(path,*args,**kwargs)
        if path==service.root:created=True
        return result
    def checked():
        if created:raise ProcessingError('review_store_unsafe')
        return original_check()
    monkeypatch.setattr(Path,'mkdir',changed_after_mkdir)
    monkeypatch.setattr(service,'_path',checked)
    with pytest.raises(ProcessingError,match='review_store_unsafe'):
        service.request('2026-01',fingerprint,'Synthetic evidence')
    assert not (service.root/'requests.sqlite3').exists()


def test_review_closes_connections_including_duplicate_return_and_history(reviewing,monkeypatch):
    import sqlite3
    _,_,service=reviewing
    fingerprint=service.capture('2026-01')['fingerprint']
    database=service.root/'requests.sqlite3'
    connect=sqlite3.connect
    connections=[]
    def tracked(target,*args,**kwargs):
        connection=connect(target,*args,**kwargs)
        if str(target)==str(database) or str(target).startswith(database.as_uri()):
            connections.append(connection)
        return connection
    monkeypatch.setattr(sqlite3,'connect',tracked)
    first=service.request('2026-01',fingerprint,'Synthetic closure evidence')
    assert service.request('2026-01',fingerprint,'Synthetic closure evidence')==first
    assert service.history()==[first] and len(connections)==3
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError,match='closed'):
            connection.execute('SELECT 1')


def test_interrupted_review_schema_rolls_back_and_next_request_recovers(reviewing,monkeypatch):
    import sqlite3
    from contextlib import closing
    _,engine,service=reviewing
    fingerprint=service.capture('2026-01')['fingerprint']
    before=engine.store.history()
    database=service.root/'requests.sqlite3'
    connect=sqlite3.connect
    class Interrupted(sqlite3.Connection):
        def execute(self,sql,*args,**kwargs):
            if sql.startswith('CREATE TRIGGER IF NOT EXISTS no_delete'):
                raise sqlite3.OperationalError('Synthetic interruption before complete schema')
            return super().execute(sql,*args,**kwargs)
    def interrupted(target,*args,**kwargs):
        if str(target)==str(database):kwargs['factory']=Interrupted
        return connect(target,*args,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(sqlite3,'connect',interrupted)
        with pytest.raises(sqlite3.OperationalError,match='Synthetic interruption'):
            service.request('2026-01',fingerprint,'Synthetic atomic schema evidence')
    with closing(connect(database)) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name IN ('requests','no_update','no_delete')").fetchall()==[]
    record=service.request('2026-01',fingerprint,'Synthetic atomic schema evidence')
    assert service.history()==[record] and engine.store.history()==before
