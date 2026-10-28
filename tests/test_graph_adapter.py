"""Graph protocol simulations only; every response/session is synthetic."""
from dataclasses import replace
from hashlib import sha256
from threading import Event

import pytest

from test_msal_foundation import CONFIG, FakeMsal
from report_samples import service_csv
from equipment_data_manager.auth.msal_session import MsalSession
from equipment_data_manager.storage.contracts import StorageError
from equipment_data_manager.storage.graph_adapter import OfflineGraphAdapter, GraphResponse as R, GraphScope, PROBE_CONTENT
from equipment_data_manager.storage.discovery import discover_reports
from equipment_data_manager.storage.source import ProviderFileSource
from equipment_data_manager.processing.models import ReportType
from equipment_data_manager.ui.workflow import DesktopWorkflow, SourceFile

SCOPE=GraphScope('synthetic-site','synthetic-drive',('raw-repairs','raw-services','raw-tma'),
                 'nonproduction-probes',('download.example.test',))
DATA=b'synthetic report bytes only'


def item(*,id='item-1',name='same.csv',parent='raw-repairs',body=DATA,version='"v1"',**changes):
    result=dict(id=id,name=name,size=len(body),eTag=version,file={},
                parentReference={'driveId':SCOPE.drive_id,'id':parent})
    result.update(changes);return result


class FakeTransport:
    def __init__(self,responses):self.responses=list(responses);self.calls=[]
    def request(self,method,target,*,headers,body,timeout):
        self.calls.append(dict(method=method,target=target,headers=headers,body=body,timeout=timeout))
        response=self.responses.pop(0)
        if isinstance(response,Exception):raise response
        return response


def adapter(responses,**kwargs):
    fake=FakeTransport(responses);client=FakeMsal();session=MsalSession(CONFIG,client,clock=lambda:100)
    delays=[]
    instance=OfflineGraphAdapter(SCOPE,session,fake,sleeper=delays.append,clock=lambda:0,**kwargs)
    return instance,fake,session,delays


def test_pagination_preserves_duplicate_names_by_distinct_ids_and_never_recurses():
    path='/v1.0/drives/synthetic-drive/items/raw-repairs/children'
    api,transport,_,_=adapter([R(200,{'value':[item(),{'id':'history','folder':{}}],
        '@odata.nextLink':'https://graph.microsoft.com'+path+'?$skiptoken=next'}),
        R(200,{'value':[item(id='item-2')]})])
    files=api.list_files('raw-repairs')
    assert len(files)==2 and files[0].name==files[1].name and files[0].item_id!=files[1].item_id
    assert len(transport.calls)==2 and transport.calls[1]['target']==path+'?$skiptoken=next'
    assert all(c['timeout']==30 for c in transport.calls)


@pytest.mark.parametrize('link',[
    'https://attacker.example.test/v1.0/drives/synthetic-drive/items/raw-repairs/children',
    'http://graph.microsoft.com/v1.0/drives/synthetic-drive/items/raw-repairs/children',
    'https://graph.microsoft.com/v1.0/me/drive/children',
    'https://graph.microsoft.com@attacker.example.test/v1.0/drives/synthetic-drive/items/raw-repairs/children'])
def test_nextlink_never_changes_graph_host_or_authorized_endpoint(link):
    api,transport,_,_=adapter([R(200,{'value':[],'@odata.nextLink':link})])
    with pytest.raises(StorageError,match='pagination_rejected'):api.list_files('raw-repairs')
    assert len(transport.calls)==1


def test_site_and_library_selection_are_scoped_and_document_libraries_only():
    api,transport,_,_=adapter([R(200,{'id':'synthetic-site','displayName':'Synthetic Site'}),
        R(200,{'value':[{'id':'library-1','name':'Synthetic Documents','driveType':'documentLibrary'},
                         {'id':'personal','name':'Not organizational library','driveType':'personal'}]})])
    assert api.site()['id']=='synthetic-site'
    assert api.libraries()==({'id':'library-1','name':'Synthetic Documents'},)
    assert all('/sites/synthetic-site' in c['target'] for c in transport.calls)
    with pytest.raises(StorageError,match='not_authorized'):api.list_files('other-folder')


@pytest.mark.parametrize('status,code',[(401,'auth_session_expired'),(403,'storage_access_denied'),
    (404,'storage_folder_missing'),(409,'storage_conflict'),(412,'storage_conflict')])
def test_permissions_expired_sessions_missing_folders_and_conflicts_do_not_retry(status,code):
    api,transport,session,_=adapter([R(status)])
    with pytest.raises(StorageError,match=code):api.list_files('raw-repairs')
    assert len(transport.calls)==1
    if status==401:
        with pytest.raises(StorageError,match='session_expired'):session.token()


def test_retries_respect_retry_after_and_partial_network_failures_restart_get():
    api,transport,_,delays=adapter([R(429,headers={'Retry-After':'1'}),TimeoutError('PRIVATE URL'),
                                  R(200,{'value':[item()]})])
    assert len(api.list_files('raw-repairs'))==1
    assert delays==[1,0.5] and len(transport.calls)==3
    assert all(c['method']=='GET' for c in transport.calls)


@pytest.mark.parametrize('responses,code',[
    ([R(503)]*3,'storage_retry_exhausted'),([OSError('PRIVATE')]*3,'storage_network_interrupted'),
    ([R(429,headers={'Retry-After':'60'})],'storage_retry_later')])
def test_bounded_retries_and_long_server_wait_never_retry_early(responses,code):
    api,transport,_,delays=adapter(responses)
    with pytest.raises(StorageError,match=code) as error:api.list_files('raw-repairs')
    assert 'PRIVATE' not in str(error.value) and len(transport.calls)<=3
    assert not delays if code=='storage_retry_later' else True


def test_download_checks_expected_version_hash_length_and_metadata_after_read():
    metadata=item()
    api,transport,_,_=adapter([R(200,{'value':[metadata]}),R(200,metadata),R(200,body=DATA),R(200,metadata)])
    source,=api.list_files('raw-repairs')
    result=api.read(source,expected_sha256=sha256(DATA).hexdigest())
    assert result.content==DATA and result.sha256==sha256(DATA).hexdigest() and not result.sync_verified
    assert 'expected_sha256' in result.integrity
    assert [c['target'] for c in transport.calls][-2:]==[
        '/v1.0/drives/synthetic-drive/items/item-1/content','/v1.0/drives/synthetic-drive/items/item-1']


@pytest.mark.parametrize('problem', ['hash','partial','changed_before','changed_after','wrong_parent'])
def test_failed_download_never_returns_processing_bytes(problem):
    original=item();before=item(version='"v2"') if problem=='changed_before' else original
    after=item(version='"v2"') if problem=='changed_after' else original
    if problem=='wrong_parent':before=item(parent='other-folder')
    api,_,_,_=adapter([R(200,{'value':[original]}),R(200,before),R(200,body=DATA[:-1] if problem=='partial' else DATA),R(200,after)])
    source,=api.list_files('raw-repairs')
    with pytest.raises(StorageError):api.read(source,expected_sha256='0'*64 if problem=='hash' else None)


def test_interrupted_content_download_retries_get_and_rechecks_final_version():
    metadata=item()
    api,transport,_,delays=adapter([R(200,{'value':[metadata]}),R(200,metadata),
        OSError('partial transfer'),R(200,body=DATA),R(200,metadata)])
    source,=api.list_files('raw-repairs')
    assert api.read(source).content==DATA and delays==[0.25]
    assert transport.calls[2]['target']==transport.calls[3]['target']


def test_download_redirect_is_allowlisted_and_never_receives_bearer_token():
    metadata=item();url='https://download.example.test/content?SYNTHETIC_SIGNED_QUERY=only'
    api,transport,_,_=adapter([R(200,{'value':[metadata]}),R(200,metadata),
        R(302,headers={'Location':url}),R(200,body=DATA),R(200,metadata)])
    source,=api.list_files('raw-repairs');assert api.read(source).content==DATA
    assert transport.calls[3]['headers']=={} and transport.calls[3]['target']==url
    assert 'Authorization' in transport.calls[2]['headers']
    api,transport,_,_=adapter([R(200,{'value':[metadata]}),R(200,metadata),
        R(302,headers={'Location':'https://unexpected.example.test/data'})])
    source,=api.list_files('raw-repairs')
    with pytest.raises(StorageError,match='redirect_rejected'):api.read(source)
    assert len(transport.calls)==3


def test_fixed_nonproduction_probe_uses_create_only_and_verifies_uploaded_bytes():
    metadata=item(id='probe-1',name='connectivity.txt',parent='nonproduction-probes',body=PROBE_CONTENT)
    api,transport,_,_=adapter([R(201,metadata),R(200,metadata),R(200,body=PROBE_CONTENT),R(200,metadata)])
    saved=api.upload_probe('connectivity.txt')
    assert saved.parent_id=='nonproduction-probes'
    request=transport.calls[0]
    assert request['body']==PROBE_CONTENT and request['headers']['If-None-Match']=='*'
    assert 'conflictBehavior=fail' in request['target']
    with pytest.raises(StorageError,match='publication_not_implemented'):
        api.create_output('approved',name='candidate.csv',content=b'CandidateUnverified')
    with pytest.raises(StorageError,match='probe_name_rejected'):api.upload_probe('candidate.csv')
    assert len(transport.calls)==4


def test_upload_conflict_or_unknown_outcome_never_causes_automatic_write_retry():
    for response,code in [(R(409),'storage_conflict'),(OSError('connection lost'),'storage_upload_outcome_unknown')]:
        api,transport,_,delays=adapter([response])
        with pytest.raises(StorageError,match=code):api.upload_probe('probe.txt')
        assert len(transport.calls)==1 and not delays


def test_unknown_probe_upload_recovers_by_explicit_list_and_verify_not_reupload():
    metadata=item(id='probe',name='probe.txt',parent='nonproduction-probes',body=PROBE_CONTENT)
    api,transport,_,_=adapter([OSError('server may have created it'),R(200,{'value':[metadata]}),
        R(200,metadata),R(200,body=PROBE_CONTENT),R(200,metadata)])
    with pytest.raises(StorageError,match='outcome_unknown'):api.upload_probe('probe.txt')
    source,=api.probe_files();assert api.verify_probe(source).content==PROBE_CONTENT
    assert sum(c['method']=='PUT' for c in transport.calls)==1


def test_corrupt_uploaded_probe_is_not_treated_as_verified_or_published():
    metadata=item(id='probe',name='probe.txt',parent='nonproduction-probes',body=PROBE_CONTENT)
    wrong=b'X'*len(PROBE_CONTENT)
    api,transport,_,_=adapter([R(201,metadata),R(200,metadata),R(200,body=wrong)])
    with pytest.raises(StorageError,match='hash_mismatch'):api.upload_probe('probe.txt')
    assert len(transport.calls)==3


def test_mock_graph_bridge_previews_and_processes_with_real_engine_locally(tmp_path):
    data=service_csv(1,3);metadata=item(name='service.csv',body=data)
    api,transport,_,_=adapter([R(200,{'value':[metadata]})]+[R(200,metadata),R(200,body=data),R(200,metadata)]*2)
    source,=api.list_files('raw-repairs')
    workflow=DesktopWorkflow(tmp_path/'local-candidates',source=ProviderFileSource(api,{'selected':source}),output_format='powerbi')
    preview=workflow.preview([SourceFile('selected',source.name)],ReportType.SERVICE_ORDERS,'2026-01',lambda *a:None,Event())
    assert preview[0].result.status=='success' and not (tmp_path/'local-candidates').exists()
    result=workflow.process(preview,{},lambda *a:None,Event())[0].result
    assert result.status=='success' and result.output_rows==3
    assert all(c['method']=='GET' for c in transport.calls)
    assert result.output_location.is_relative_to(tmp_path/'local-candidates')


def test_invalid_scope_and_discovery_missing_folder_are_not_guessed():
    with pytest.raises(StorageError):GraphScope('site','drive',('raw',),'raw')
    api,_,_,_=adapter([R(404),R(404),R(404)])
    selection=discover_reports(api,'2026-01',{ReportType.REPAIRS:'raw-repairs',ReportType.SERVICE_ORDERS:'raw-services',
                                           ReportType.TMA_WORK_ORDERS:'raw-tma'})
    assert len(selection.missing)==3 and all(code=='storage_folder_missing' for _,code in selection.issues)


def test_scope_rejects_strings_masquerading_as_folder_or_host_allowlists():
    with pytest.raises(StorageError):GraphScope('site','drive','raw-folder')
    with pytest.raises(StorageError):GraphScope('site','drive',('raw',),download_hosts='download.example.test')


def test_expired_content_link_does_not_mislabel_organizational_session():
    metadata=item()
    api,_,session,_=adapter([R(200,{'value':[metadata]}),R(200,metadata),
        R(302,headers={'Location':'https://download.example.test/content'}),R(401)])
    source,=api.list_files('raw-repairs')
    with pytest.raises(StorageError,match='download_link_expired'):api.read(source)
    assert session.token().value=='SYNTHETIC_TOKEN_ONLY'


def test_offline_demo_requires_no_sdk_credentials_or_network_and_writes_no_outputs(tmp_path,monkeypatch):
    import importlib.util
    from pathlib import Path
    import socket
    spec=importlib.util.spec_from_file_location('offline_graph_demo',Path(__file__).parents[1]/'examples/sharepoint_foundation_demo.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(socket,'create_connection',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('Network forbidden')))
    result=module.preview(tmp_path/'no-output')
    assert result['mode']=='mock_graph' and result['preview_status']=='success'
    assert result['live_authentication'] is result['publication_enabled'] is result['outputs_written'] is False
