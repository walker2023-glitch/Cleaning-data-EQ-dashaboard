"""Review-packet long path and failure safety; all reports/paths are synthetic."""
from base64 import b32decode
from hashlib import sha256
import json
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace
from uuid import UUID

import pytest

import equipment_data_manager.monthly as monthly
from equipment_data_manager.monthly import Workspace, export_review_packet
from equipment_data_manager.processing.models import ProcessingError
from equipment_data_manager.processing.repair_financial import summary_name
from test_monthly_workflow import populate, process

VIRTUAL_ROOT=PureWindowsPath('C:/Users/synthetic11/AppData/Local/Temp/pytest-of-synthetic11/pytest-100/test_business_review_handles_m0/synthetic-review/candidates')


def units(path):
    return len(str(path).encode('utf-16-le'))//2


@pytest.fixture
def prepared(tmp_path):
    workspace=Workspace(tmp_path/'raw',tmp_path/'candidates',tmp_path/'reserved')
    populate(workspace)
    workflow,_=process(workspace)
    return workspace,workflow.coordinator


def windows_target(workspace,path,root=VIRTUAL_ROOT):
    return root/PureWindowsPath(*path.relative_to(workspace.candidate_folder).parts)


def test_parent_exists_but_old_summary_path_crosses_classic_windows_limit(prepared,monkeypatch):
    workspace,coordinator=prepared
    old=workspace.candidate_folder/'review_packets'/('.staging-'+'a'*32)/'repair_financial_summary'/summary_name('2026-01')
    old.parent.mkdir(parents=True)
    real_open=Path.open;observed=[]
    def bounded(path,*args,**kwargs):
        if path.is_relative_to(workspace.candidate_folder/'review_packets'):
            target=windows_target(workspace,path)
            observed.append((path.parent.is_dir(),units(target)))
            if units(target)>=260:
                raise FileNotFoundError(2,'Synthetic Win32 MAX_PATH failure',str(path))
        return real_open(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',bounded)
    assert units(windows_target(workspace,old))==260
    with pytest.raises(FileNotFoundError):old.write_bytes(b'Synthetic')
    assert observed[-1][0] is True  # Missing directory was NOT the cause.
    # Real exporter on the SAME emulated Windows root now succeeds, including reads.
    packet=export_review_packet(workspace,coordinator,'2026-01')
    manifest=json.loads((packet/'packet.json').read_text())
    entry,=manifest['supplemental_files']
    data=(packet/entry['file']).read_bytes()
    assert sha256(data).hexdigest()==entry['sha256']
    assert units(windows_target(workspace,packet/entry['file']))<260
    assert not workspace.approved_folder.exists()


def test_short_temp_root_also_avoids_old_path_failure_without_missing_parent(tmp_path):
    relative=PureWindowsPath('review_packets')/('.staging-'+'a'*32)/'repair_financial_summary'/summary_name('2026-01')
    assert units(VIRTUAL_ROOT/relative)==260
    assert units(PureWindowsPath('C:/edm-temp/candidates')/relative)<260
    target=tmp_path/'.staging-synthetic'/'repair_financial_summary'/summary_name('2026-01')
    target.parent.mkdir(parents=True)
    assert target.parent.is_dir()
    target.write_bytes(b'Synthetic')
    assert target.read_bytes()==b'Synthetic'


def test_compact_uuid_keeps_all_bits_and_is_case_insensitive_filesystem_safe(monkeypatch):
    identity=UUID('12345678-9abc-4def-8abc-123456789abc')
    monkeypatch.setattr(monthly,'uuid4',lambda:identity)
    token=monthly._packet_identifier()
    assert len(token)==26 and token==token.lower()
    assert set(token)<=set('abcdefghijklmnopqrstuvwxyz234567')
    assert b32decode(token.upper()+'='*((-len(token))%8))==identity.bytes


def test_path_preflight_counts_utf16_and_checks_final_paths():
    staged=PureWindowsPath('C:/local/review_packets/.s-'+'a'*26)
    final=PureWindowsPath('C:/local/review_packets/2026-01-'+'a'*26)
    relative=PureWindowsPath('summary')/('a'*(259-units(final/'summary'/'x')+1))
    assert units(final/relative)==259
    monthly._check_windows_packet_paths(staged,final,[relative])
    # A supplementary character occupies TWO UTF-16 code units, even though len=1.
    too_long=relative.with_name(relative.name[:-1]+'\U0001F9F9')
    assert units(final/too_long)==260 and units(staged/too_long)<260
    with pytest.raises(ProcessingError,match='review_packet_path_too_long'):
        monthly._check_windows_packet_paths(staged,final,[too_long])


def test_too_long_windows_destination_rejects_before_staging(prepared,monkeypatch):
    workspace,coordinator=prepared
    before={p:p.read_bytes() for p in workspace.candidate_folder.rglob('*') if p.is_file()}
    def reject(*args):raise ProcessingError('review_packet_path_too_long')
    monkeypatch.setattr(monthly,'sys',SimpleNamespace(platform='win32'))
    monkeypatch.setattr(monthly,'_check_windows_packet_paths',reject)
    with pytest.raises(ProcessingError,match='review_packet_path_too_long'):
        export_review_packet(workspace,coordinator,'2026-01')
    assert not (workspace.candidate_folder/'review_packets').exists()
    assert {p:p.read_bytes() for p in workspace.candidate_folder.rglob('*') if p.is_file()}==before


@pytest.mark.parametrize('failure',['missing_parent','permissions','fsync','rename'])
def test_summary_io_failures_cleanup_only_own_stage_and_preserve_prior_packet(prepared,monkeypatch,failure):
    workspace,coordinator=prepared
    old=export_review_packet(workspace,coordinator,'2026-01')
    old_bytes={p:p.read_bytes() for p in old.rglob('*') if p.is_file()}
    source_bytes={p:p.read_bytes() for p in workspace.raw_folder.rglob('*') if p.is_file()}
    real_open,real_rename,real_fsync=Path.open,Path.rename,monthly.os.fsync
    reached={'summary':False}
    def opening(path,*args,**kwargs):
        mode=args[0] if args else kwargs.get('mode','r')
        if mode=='xb' and path.parent.name=='repair_financial_summary' and path.parent.parent.name.startswith('.s-'):
            assert path.parent.is_dir()
            reached['summary']=True
            if failure=='missing_parent':path.parent.rmdir()
            if failure=='permissions':raise PermissionError('Synthetic denied')
        return real_open(path,*args,**kwargs)
    def fsync(fd):
        if reached['summary'] and failure=='fsync':raise OSError('Synthetic fsync failure')
        return real_fsync(fd)
    def rename(path,target):
        if path.name.startswith('.s-') and failure=='rename':raise PermissionError('Synthetic rename failure')
        return real_rename(path,target)
    monkeypatch.setattr(Path,'open',opening)
    monkeypatch.setattr(Path,'rename',rename)
    monkeypatch.setattr(monthly.os,'fsync',fsync)
    with pytest.raises(OSError):export_review_packet(workspace,coordinator,'2026-01')
    assert reached['summary']
    assert list((workspace.candidate_folder/'review_packets').iterdir())==[old]
    assert {p:p.read_bytes() for p in old.rglob('*') if p.is_file()}==old_bytes
    assert {p:p.read_bytes() for p in workspace.raw_folder.rglob('*') if p.is_file()}==source_bytes
    assert len(coordinator.store.history())==3 and not workspace.approved_folder.exists()


def test_repeat_identifier_never_replaces_an_existing_packet(prepared,monkeypatch):
    workspace,coordinator=prepared
    monkeypatch.setattr(monthly,'_packet_identifier',lambda:'a'*26)
    packet=export_review_packet(workspace,coordinator,'2026-01')
    before={p:p.read_bytes() for p in packet.rglob('*') if p.is_file()}
    with pytest.raises(FileExistsError):export_review_packet(workspace,coordinator,'2026-01')
    assert {p:p.read_bytes() for p in packet.rglob('*') if p.is_file()}==before
    assert list(packet.parent.iterdir())==[packet]


def test_windows_preflight_measures_absolute_paths_for_relative_workspace(prepared,monkeypatch):
    original,coordinator=prepared
    monkeypatch.chdir(original.candidate_folder.parent)
    workspace=Workspace(Path('raw'),Path('candidates'),Path('reserved'))
    calls=[]
    def check(stage,final,relatives):
        calls.append((stage,final))
        assert stage.is_absolute() and final.is_absolute()
        assert stage.parent==original.candidate_folder/'review_packets'
        raise ProcessingError('review_packet_path_too_long')
    monkeypatch.setattr(monthly,'sys',SimpleNamespace(platform='win32'))
    monkeypatch.setattr(monthly,'_check_windows_packet_paths',check)
    with pytest.raises(ProcessingError,match='review_packet_path_too_long'):
        export_review_packet(workspace,coordinator,'2026-01')
    assert len(calls)==1 and not (original.candidate_folder/'review_packets').exists()
