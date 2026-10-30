"""Synthetic configurations/bytes; official MSAL cache only, no real OAuth/network."""
import base64
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from threading import Event

import pytest
from report_samples import service_csv
from test_msal_foundation import TENANT,CLIENT,FakeProtector
from equipment_data_manager.auth.msal_session import OrganizationalConfig
from equipment_data_manager.auth.managed_msal import create_session,CacheLease
from equipment_data_manager.m365_config import TestPilotConfig as Config,SyntheticFile,load_test_config
from equipment_data_manager.m365_pilot import ReadOnlyTestPilot,save_origin
from equipment_data_manager.storage.graph_adapter import GraphScope,GraphResponse as R
from equipment_data_manager.storage.https_transport import ReadOnlyHttpsTransport,MsalHttpsClient
from equipment_data_manager.storage.contracts import StorageError
from equipment_data_manager.processing.models import ReportType

OID='33333333-3333-3333-3333-333333333333'
RAW=service_csv(1,3)


@pytest.fixture
def config(tmp_path):
    return Config(OrganizationalConfig(TENANT,CLIENT,('Sites.Selected',)),
        GraphScope('synthetic-site','synthetic-drive',('raw-repairs','raw-services','raw-tma'),
            download_hosts=('synthetic.sharepoint.com',)),
        (SyntheticFile('item-1',ReportType.SERVICE_ORDERS,sha256(RAW).hexdigest()),),
        tmp_path/'auth'/TENANT/CLIENT/'msal-cache.bin',True,'Synthetic IT test authorization reference')


class FakeHttp:
    def __init__(self):self.closed=False
    def close(self):self.closed=True


class FakeSdk:
    def __init__(self,*args,**kwargs):
        self.args=args;self.kwargs=kwargs
        self.accounts=[dict(realm=TENANT,local_account_id=OID,home_account_id='synthetic-account')]
        self.result=dict(access_token='SYNTHETIC_ACCESS_ONLY',expires_in=3600,id_token_claims=dict(tid=TENANT,oid=OID))
        self.interactive=[];self.silent=[]
    def get_accounts(self):return self.accounts
    def acquire_token_silent(self,*args,**kwargs):self.silent.append(kwargs);return self.result
    def acquire_token_interactive(self,**kwargs):self.interactive.append(kwargs);return self.result
    def remove_account(self,account):self.accounts.remove(account)


def session(config,**kwargs):
    return create_session(config,operator_authorized=True,client_factory=FakeSdk,protector=FakeProtector(),http=FakeHttp(),**kwargs)


def config_text(config):
    return f'''[test_pilot]
enabled = true
environment = "nonproduction"
authorization_reference = "Synthetic IT test authorization reference"
[organization]
tenant_id = "{TENANT}"
client_id = "{CLIENT}"
scopes = ["Sites.Selected"]
[resources]
site_id = "synthetic-site"
drive_id = "synthetic-drive"
raw_folder_ids = ["raw-repairs","raw-services","raw-tma"]
download_hosts = ["synthetic.sharepoint.com"]
[cache]
path = "{config.cache_path.as_posix()}"
[[synthetic_files]]
item_id = "item-1"
report_type = "service_orders"
sha256 = "{sha256(RAW).hexdigest()}"
'''


def test_config_parse_is_offline_and_blocks_unknown_fields_and_permission_fallback(config,tmp_path):
    path=tmp_path/'test.toml';path.write_text(config_text(config))
    assert load_test_config(path)==config
    assert not config.cache_path.exists()
    for text in [config_text(config).replace('Sites.Selected','Sites.ReadWrite.All'),
                 config_text(config).replace('Sites.Selected','Sites.Read.All'),
                 config_text(config).replace('nonproduction','production'),
                 config_text(config).replace('synthetic.sharepoint.com','attacker.example'),
                 config_text(config).replace('client_id =', 'client_secret = "forbidden"\nclient_id =')]:
        path.write_text(text)
        with pytest.raises(StorageError):load_test_config(path)


@pytest.mark.parametrize('enabled,permission',[(False,False),(True,False),(False,True)])
def test_live_gate_runs_before_sdk_construction_or_cache_creation(config,enabled,permission):
    calls=[]
    with pytest.raises(StorageError,match='not_authorized'):
        create_session(replace(config,enabled=enabled),operator_authorized=permission,client_factory=lambda *a,**k:calls.append(True))
    assert calls==[] and not config.cache_path.parent.exists()


def test_bootstrap_passes_official_sdk_tenant_public_client_and_safe_options(config):
    current=session(config)
    assert current.client.kwargs['authority']=='https://login.microsoftonline.com/'+TENANT
    assert current.client.kwargs['instance_discovery'] is False
    assert current.client.kwargs['enable_pii_log'] is False
    assert current.client.kwargs['client_capabilities']==['CP1']
    assert 'client_credential' not in current.client.kwargs
    current.sign_in()
    assert current.account_id=='synthetic-account'
    assert current.client.interactive[0]['timeout']==120
    assert 'SYNTHETIC_ACCESS_ONLY' not in repr(current.token())
    current.sign_out()
    assert current.connection_status=='signed_out_locally' and current.closed
    assert config.cache_path.exists() and not Path(str(config.cache_path)+'.session.lock').exists()
    with pytest.raises(StorageError,match='signed_out'):current.token()


def test_whole_session_lease_blocks_stale_multi_process_cache_writers(config):
    first=session(config)
    try:
        with pytest.raises(StorageError,match='auth_cache_busy'):session(config)
    finally:first.close()
    second=session(config);second.close()


@pytest.mark.parametrize('result,code',[
    ({'error':'access_denied','error_description':'PRIVATE_SDK_DETAILS'},'permission_denied'),
    ({'error':'interaction_required'},'interaction_required'),
    ({'access_token':'SYNTHETIC','expires_in':3600,'id_token_claims':{'tid':'wrong','oid':OID}},'wrong_tenant'),
    ({'access_token':'SYNTHETIC','expires_in':3600,'id_token_claims':{'tid':TENANT}},'subject_invalid'),
    ({'access_token':'unsafe\nheader','expires_in':3600,'id_token_claims':{'tid':TENANT,'oid':OID}},'invalid_token_result')])
def test_failed_sign_in_invalidates_prior_access_and_never_exposes_sdk_description(config,result,code):
    current=session(config);current.sign_in();current.client.result=result
    try:
        with pytest.raises(StorageError,match=code) as error:current.sign_in()
        assert current._token is None and 'PRIVATE' not in str(error.value)
    finally:current.close()


def test_claims_challenge_requires_explicit_interaction_and_is_forwarded_only_to_sdk(config):
    current=session(config);current.sign_in()
    claims={'access_token':{'synthetic_claim':{'essential':True}}}
    encoded=base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=')
    current.record_challenge('Bearer error="insufficient_claims", claims="'+encoded+'"')
    with pytest.raises(StorageError,match='interaction_required'):current.token()
    assert len(current.client.interactive)==1
    current.sign_in()
    assert json.loads(current.client.interactive[-1]['claims_challenge'])==claims
    current.close()


@pytest.mark.parametrize('header',['Bearer claims="invalid"','Bearer claims=""','Bearer claims="'+('a'*17000)+'"'])
def test_malformed_claims_challenges_are_safe_and_invalidate_tokens(config,header):
    current=session(config);current.sign_in()
    try:
        with pytest.raises(StorageError,match='claims_challenge_invalid'):current.record_challenge(header)
        assert current._token is None
    finally:current.close()


def test_cache_failure_during_signout_reports_incomplete_not_success(config,monkeypatch):
    current=session(config);current.sign_in()
    monkeypatch.setattr(current.persistence,'save',lambda cache:(_ for _ in ()).throw(OSError('PRIVATE')))
    with pytest.raises(StorageError,match='auth_sign_out_incomplete') as error:current.sign_out()
    assert current._token is None and current.closed and 'PRIVATE' not in str(error.value)
    assert current.connection_status!='signed_out_locally'


class Response:
    def __init__(self,status=200,body=b'bytes',headers=None):
        self.status_code=status;self.body=body;self.headers=headers or {};self.closed=False
    def iter_content(self,chunk_size):
        if isinstance(self.body,Exception):raise self.body
        yield self.body
    def close(self):self.closed=True


class HttpSession:
    def __init__(self,response):self.response=response;self.calls=[];self.closed=False
    def request(self,*args,**kwargs):self.calls.append((args,kwargs));return self.response
    def close(self):self.closed=True


def test_https_transport_tls_timeouts_no_redirect_no_netrc_and_bounded_body():
    response=Response(headers={'Content-Length':'5'})
    http=HttpSession(response);transport=ReadOnlyHttpsTransport(('synthetic.sharepoint.com',),session=http)
    result=transport.request('GET','/v1.0/sites/synthetic',headers={'Authorization':'Bearer SYNTHETIC'},body=None,timeout=30)
    assert result.body==b'bytes' and response.closed
    kwargs=http.calls[0][1]
    assert kwargs['verify'] is True and kwargs['allow_redirects'] is False and kwargs['timeout']==(10,30)
    assert kwargs['auth'] is not None and transport.last_diagnostic=='http_200'


@pytest.mark.parametrize('method,target,headers',[
    ('PUT','/v1.0/sites/synthetic',{}),('POST','/v1.0/sites/synthetic',{}),('DELETE','/v1.0/sites/synthetic',{}),
    ('GET','http://graph.microsoft.com/v1.0/sites/synthetic',{}),
    ('GET','https://graph.microsoft.com@attacker.example/v1.0/sites/synthetic',{}),
    ('GET','https://graph.microsoft.com:443/v1.0/sites/synthetic',{}),
    ('GET','https://attacker.example/download',{}),
    ('GET','https://synthetic.sharepoint.com/download',{'Authorization':'Bearer SYNTHETIC'})])
def test_transport_rejects_writes_untrusted_targets_and_cdn_bearers_before_io(method,target,headers):
    http=HttpSession(Response());transport=ReadOnlyHttpsTransport(('synthetic.sharepoint.com',),session=http)
    with pytest.raises(StorageError):transport.request(method,target,headers=headers,body=None,timeout=30)
    assert http.calls==[]


@pytest.mark.parametrize('response,code',[
    (Response(body=b'too long',headers={'Content-Length':'100'}),'storage_file_too_large'),
    (Response(body=b'long data'),'storage_file_too_large'),
    (Response(body=TimeoutError('PRIVATE_SIGNED_URL')),'m365_network_or_tls_failure'),
    (Response(body=b'bad',headers={'Content-Length':'5'}),'m365_network_or_tls_failure')])
def test_partial_or_interrupted_or_oversize_transfers_close_and_redact(response,code):
    transport=ReadOnlyHttpsTransport((),session=HttpSession(response),max_bytes=5)
    with pytest.raises((StorageError,OSError),match=code) as error:
        transport.request('GET','/v1.0/drives/synthetic/items/file/content',headers={},body=None,timeout=30)
    assert 'PRIVATE' not in str(error.value) and response.closed


def test_auth_http_transport_limits_host_tls_and_redirects():
    response=Response(status=302);http=HttpSession(response);client=MsalHttpsClient(session=http)
    with pytest.raises(StorageError,match='authority_redirect_rejected'):
        client.get('https://login.microsoftonline.com/synthetic/v2.0/.well-known/openid-configuration')
    assert http.calls[0][1]['allow_redirects'] is False and http.calls[0][1]['verify'] is True
    with pytest.raises(StorageError,match='authority_rejected'):
        client.post('https://attacker.example/token',data={'synthetic':'only'})
    assert len(http.calls)==1


class DiscoveryHttp(FakeHttp):
    def __init__(self):super().__init__();self.calls=[]
    def get(self,url,**kwargs):
        self.calls.append(url)
        class Metadata:
            status_code=200
            headers={'Content-Type':'application/json'}
            def json(self):
                root='https://login.microsoftonline.com/'+TENANT
                return dict(authorization_endpoint=root+'/oauth2/v2.0/authorize',
                    token_endpoint=root+'/oauth2/v2.0/token',issuer=root+'/v2.0',
                    jwks_uri=root+'/discovery/v2.0/keys')
            @property
            def text(self):return json.dumps(self.json())
        return Metadata()


def test_real_official_msal_construction_uses_only_injected_metadata_and_no_auth_attempt(config):
    import msal
    http=DiscoveryHttp()
    current=create_session(config,operator_authorized=True,protector=FakeProtector(),http=http)
    try:
        assert isinstance(current.client,msal.PublicClientApplication)
        assert isinstance(current.cache,msal.SerializableTokenCache)
        assert http.calls and all(url.startswith('https://login.microsoftonline.com/'+TENANT+'/') for url in http.calls)
        with pytest.raises(StorageError,match='account_selection_required'):current.token()
    finally:current.close()


class GraphHttp:
    def __init__(self,config):
        self.config=config;self.calls=[];self.version='"synthetic-v1"';self.body=RAW
        self.read_error=None;self.denied=False;self.closed=False;self.redirect=False
    def metadata(self):
        kind=self.config.files[0].report_type
        folder=self.config.scope.raw_folder_ids[list(ReportType).index(kind)]
        name='synthetic.xlsx' if kind==ReportType.TMA_WORK_ORDERS else 'synthetic.csv'
        return dict(id='item-1',name=name,size=len(self.body),eTag=self.version,
            file={'hashes':{'sha256Hash':sha256(self.body).hexdigest()}},
            parentReference={'driveId':'synthetic-drive','id':folder})
    def request(self,method,target,*,headers,body,timeout):
        assert method=='GET' and body is None
        self.calls.append((method,target,dict(headers)))
        if self.denied:return R(403)
        if target.startswith('https://synthetic.sharepoint.com/'):
            assert not headers
            return R(200,body=self.body)
        if target.endswith('/content'):
            if self.read_error:raise self.read_error
            if self.redirect:return R(302,headers={'location':'https://synthetic.sharepoint.com/download?signed=SYNTHETIC'})
            return R(200,body=self.body)
        if target=='/v1.0/sites/synthetic-site':return R(200,{'id':'synthetic-site','displayName':'Synthetic test site'})
        if target=='/v1.0/sites/synthetic-site/drives':return R(200,{'value':[{'id':'synthetic-drive','name':'Synthetic test docs','driveType':'documentLibrary'}]})
        if target.endswith('/children'):
            return R(200,{'value':[self.metadata(),dict(self.metadata(),id='not-approved-synthetic-item')]})
        if target.endswith('/items/item-1'):return R(200,self.metadata())
        folder=target.rsplit('/',1)[-1]
        return R(200,{'id':folder,'folder':{},'parentReference':{'driveId':'synthetic-drive'}})
    def close(self):self.closed=True


def connected(config,tmp_path,raw=None):
    auth=session(config);http=GraphHttp(config)
    if raw is not None:http.body=raw
    pilot=ReadOnlyTestPilot(config,auth,http,tmp_path/'candidates')
    pilot.adapter.sleeper=lambda seconds:None
    pilot.sign_in()
    return pilot,http


def test_verified_download_real_engine_preview_process_preserves_original_and_receipt(config,tmp_path):
    pilot,http=connected(config,tmp_path)
    try:
        assert pilot.mode=='offline_injected_components' and pilot.resources_verified
        files=pilot.list_reports('service_orders')
        assert len(files)==1 and files[0].item_id=='item-1'
        workflow,sources=pilot.workflow(files)
        previews=workflow.preview(sources,ReportType.SERVICE_ORDERS,'2026-01',lambda *a:None,Event())
        assert previews[0].result.status=='success' and previews[0].result.output_rows==3
        assert not pilot.output_root.exists()
        results=pilot.process(workflow,previews)
        assert results[0].result.status=='success'
        origins=list((pilot.output_root/'m365_downloads').iterdir())
        assert len(origins)==1 and (origins[0]/'original.bin').read_bytes()==RAW
        receipt=json.loads((origins[0]/'receipt.json').read_bytes())
        assert receipt['source']['item_id']=='item-1' and receipt['source']['version']=='"synthetic-v1"'
        assert receipt['download_sha256']==receipt['candidate_source_sha256']==sha256(RAW).hexdigest()
        assert receipt['approval']=='not_granted'
        repeated=pilot.process(workflow,previews)
        assert repeated[0].result.status=='skipped'
        assert len(list((pilot.output_root/'m365_downloads').iterdir()))==1
        assert len(workflow.coordinator.store.history())==1
    finally:pilot.sign_out()


def test_changed_remote_item_after_preview_fails_without_candidate_write(config,tmp_path):
    pilot,http=connected(config,tmp_path)
    try:
        workflow,sources=pilot.workflow(pilot.list_reports('service_orders'))
        previews=workflow.preview(sources,ReportType.SERVICE_ORDERS,'2026-01',lambda *a:None,Event())
        http.version='"synthetic-correction-v2"'
        result=pilot.process(workflow,previews)[0].result
        assert result.status=='failure' and result.code=='storage_source_changed'
        assert not pilot.output_root.exists()
    finally:pilot.close()


def test_partial_network_failure_retries_read_only_and_leaves_no_candidate(config,tmp_path):
    pilot,http=connected(config,tmp_path)
    try:
        workflow,sources=pilot.workflow(pilot.list_reports('service_orders'))
        http.read_error=TimeoutError('PRIVATE_SIGNED_URL')
        result=workflow.preview(sources,ReportType.SERVICE_ORDERS,'2026-01',lambda *a:None,Event())[0].result
        assert result.status=='failure' and result.code=='storage_network_interrupted'
        assert len([c for c in http.calls if c[1].endswith('/content')])==3
        assert not pilot.output_root.exists()
    finally:pilot.close()


def test_permissions_library_membership_and_readonly_writes_fail_before_action(config,tmp_path):
    pilot,http=connected(config,tmp_path)
    try:
        before=len(http.calls)
        for method in [pilot.adapter.upload_probe,pilot.adapter.create_output,pilot.adapter.probe_files]:
            with pytest.raises(StorageError,match='m365_read_only'):method('synthetic')
        assert len(http.calls)==before
        http.denied=True
        with pytest.raises(StorageError,match='access_denied'):pilot.list_reports('service_orders')
    finally:pilot.close()


def test_redirect_and_claims_never_forward_bearer_to_content_host(config,tmp_path):
    pilot,http=connected(config,tmp_path)
    try:
        http.redirect=True
        workflow,sources=pilot.workflow(pilot.list_reports('service_orders'))
        result=workflow.preview(sources,ReportType.SERVICE_ORDERS,'2026-01',lambda *a:None,Event())[0].result
        assert result.status=='success'
        assert next(c[2] for c in http.calls if c[1].startswith('https://synthetic.sharepoint.com'))=={}
        claims=base64.urlsafe_b64encode(b'{"access_token":{"synthetic":{}}}').decode()
        class Challenge:
            def request(self,*args,**kwargs):return R(401,headers={'WWW-Authenticate':'Bearer claims="'+claims+'"'})
        pilot.adapter.transport.transport=Challenge()
        with pytest.raises(StorageError,match='auth_session_expired'):pilot.adapter.list_files('raw-services')
        with pytest.raises(StorageError,match='auth_interaction_required'):pilot.session.token()
    finally:pilot.close()


def test_bad_synthetic_hash_blocks_content_before_ingestion(config,tmp_path):
    pilot,http=connected(config,tmp_path)
    try:
        workflow,sources=pilot.workflow(pilot.list_reports('service_orders'))
        wrong=replace(config,files=(replace(config.files[0],sha256='0'*64),))
        workflow.source.config=wrong
        result=workflow.preview(sources,ReportType.SERVICE_ORDERS,'2026-01',lambda *a:None,Event())[0].result
        assert result.code=='m365_synthetic_file_rejected'
        assert not any(c[1].endswith('/content') for c in http.calls)
    finally:pilot.close()


def test_expired_managed_session_never_opens_browser_without_operator_action(config):
    current=session(config);token=current.sign_in()
    current.clock=lambda:token.expires_at+60
    current.client.result={'error':'interaction_required','error_description':'PRIVATE_REASON'}
    try:
        with pytest.raises(StorageError,match='interaction_required'):current.token()
        assert len(current.client.interactive)==1 and len(current.client.silent)==1
    finally:current.close()


def test_official_serialized_cache_roundtrip_is_protected_and_signout_empties_it(config):
    current=session(config)
    current.cache.deserialize('{"AccessToken":{"synthetic":{"secret":"SYNTHETIC_CACHE_ONLY"}}}')
    current.cache.has_state_changed=True
    current.close()
    assert b'SYNTHETIC_CACHE_ONLY' not in config.cache_path.read_bytes()
    reopened=session(config)
    assert 'SYNTHETIC_CACHE_ONLY' in reopened.cache.serialize()
    reopened.sign_out()
    assert json.loads(FakeProtector().unprotect(config.cache_path.read_bytes()))=={}


def test_real_msal_auth_http_response_is_bounded_validated_and_closed():
    import requests
    response=requests.Response();response.status_code=200
    response._content=b'{"synthetic":"metadata"}';response._content_consumed=True
    response.headers={'Content-Type':'application/json'}
    http=HttpSession(response);client=MsalHttpsClient(session=http)
    result=client.get('https://login.microsoftonline.com/synthetic/v2.0/.well-known/openid-configuration')
    assert result.json()=={'synthetic':'metadata'} and http.calls[0][1]['stream'] is True
    bad=Response(body=b'PRIVATE_NON_JSON_RESPONSE')
    with pytest.raises(StorageError,match='auth_response_invalid') as error:
        MsalHttpsClient(session=HttpSession(bad)).get('https://login.microsoftonline.com/synthetic/metadata')
    assert bad.closed and 'PRIVATE' not in str(error.value)


def test_wire_loggers_do_not_emit_sensitive_response_or_signed_url(caplog):
    import logging
    from equipment_data_manager.storage.https_transport import suppress_wire_logging
    suppress_wire_logging()
    for name in ['msal','msal.oauth2cli.oauth2','urllib3.connectionpool','requests']:
        logging.getLogger(name).warning('SYNTHETIC_SIGNED_URL_OR_TOKEN')
    assert 'SYNTHETIC_SIGNED_URL_OR_TOKEN' not in caplog.text


def test_offline_component_check_imports_actual_packages_without_oauth_or_network(tmp_path):
    from equipment_data_manager.m365_components import write_component_check
    path=tmp_path/'components.json';report=write_component_check(path)
    assert report['msal']=='1.34.0' and report['requests']=='2.32.5'
    assert report['network_contacted'] is report['authentication_attempted'] is False
    assert report['publication_enabled'] is False and report['tls_roots_available']
    assert json.loads(path.read_text())==report
    with pytest.raises(FileExistsError):write_component_check(path)


def test_cache_namespace_and_synced_location_are_not_accepted(config,tmp_path):
    for path in [tmp_path/'auth/msal-cache.bin',tmp_path/'OneDrive - Synthetic'/TENANT/CLIENT/'msal-cache.bin']:
        with pytest.raises(StorageError):replace(config,cache_path=path).validate()


def test_sdk_initialization_failure_releases_lease_and_redacts_private_error(config):
    def broken(*a,**k):raise RuntimeError('PRIVATE_AUTHORITY_URI')
    with pytest.raises(StorageError,match='auth_initialization_failed') as error:
        create_session(config,operator_authorized=True,client_factory=broken,protector=FakeProtector(),http=FakeHttp())
    assert 'PRIVATE' not in str(error.value) and not Path(str(config.cache_path)+'.session.lock').exists()


def test_foreign_session_lock_is_never_removed_automatically(config):
    config.cache_path.parent.mkdir(parents=True)
    lock=Path(str(config.cache_path)+'.session.lock');lock.write_bytes(b'synthetic-foreign-session')
    with pytest.raises(StorageError,match='auth_cache_busy'):session(config)
    assert lock.read_bytes()==b'synthetic-foreign-session'


def test_default_bootstrap_protection_is_native_windows_only_and_never_plaintext(config):
    import sys
    if sys.platform!='win32':
        with pytest.raises(StorageError,match='auth_protection_unavailable'):
            create_session(config,operator_authorized=True,client_factory=FakeSdk,http=FakeHttp())
        assert not config.cache_path.parent.exists()
    else:
        current=create_session(config,operator_authorized=True,client_factory=FakeSdk,http=FakeHttp())
        current.sign_out()
        from equipment_data_manager.auth.token_cache import WindowsDpapiProtector
        assert json.loads(WindowsDpapiProtector().unprotect(config.cache_path.read_bytes()))=={}


def test_auth_metadata_cannot_redirect_browser_or_token_post_outside_tenant():
    import requests
    response=requests.Response();response.status_code=200
    response._content=b'{"authorization_endpoint":"https://attacker.example/authorize"}'
    response._content_consumed=True;response.headers={}
    http=HttpSession(response)
    with pytest.raises(StorageError,match='authority_rejected'):
        MsalHttpsClient(session=http,tenant_id=TENANT).get('https://login.microsoftonline.com/'+TENANT+'/metadata')
    assert len(http.calls)==1


def test_pilot_rejects_another_workflow_root_before_processing(config,tmp_path):
    from equipment_data_manager.ui.workflow import DesktopWorkflow
    pilot,http=connected(config,tmp_path)
    try:
        wrong=DesktopWorkflow(tmp_path/'other-root')
        with pytest.raises(StorageError,match='storage_reference_rejected'):pilot.process(wrong,[])
        assert not wrong.output_root.exists()
    finally:pilot.close()


@pytest.mark.parametrize('kind',[ReportType.REPAIRS,ReportType.TMA_WORK_ORDERS])
def test_verified_remote_bytes_use_existing_repair_and_xlsx_engines(config,tmp_path,kind):
    from test_repair_financial import raw_report
    from report_samples import tma_xlsx
    raw=raw_report() if kind==ReportType.REPAIRS else tma_xlsx(1,3)
    config=replace(config,files=(SyntheticFile('item-1',kind,sha256(raw).hexdigest()),))
    pilot,http=connected(config,tmp_path,raw)
    try:
        workflow,sources=pilot.workflow(pilot.list_reports(kind))
        previews=workflow.preview(sources,kind,'2026-01',lambda *a:None,Event())
        assert previews[0].result.status=='success' and previews[0].result.output_rows==3
        result=pilot.process(workflow,previews)[0].result
        assert result.status=='success' and result.artifact.source_hash==sha256(raw).hexdigest()
        origin=next((pilot.output_root/'m365_downloads').iterdir())
        assert (origin/'original.bin').read_bytes()==raw
        if kind==ReportType.REPAIRS:
            assert 'ReportedTotalCost' in result.output_location.read_text()
    finally:pilot.close()


@pytest.mark.parametrize('fault',['library','folder'])
def test_wrong_site_library_or_redirected_folder_blocks_discovery(config,tmp_path,fault):
    pilot,http=connected(config,tmp_path)
    original=http.request
    def corrupted(method,target,**kwargs):
        if fault=='library' and target.endswith('/drives'):
            return R(200,{'value':[{'id':'not-authorized','driveType':'documentLibrary'}]})
        if fault=='folder' and target.endswith('/items/raw-services'):
            return R(200,{'id':'raw-services','folder':{},'remoteItem':{},'parentReference':{'driveId':'synthetic-drive'}})
        return original(method,target,**kwargs)
    http.request=corrupted
    try:
        with pytest.raises(StorageError):pilot.verify_resources()
        assert pilot.resources_verified is False and not pilot.output_root.exists()
        with pytest.raises(StorageError,match='resources_not_verified'):pilot.list_reports('service_orders')
    finally:pilot.close()


def test_encoded_http_length_is_not_mistaken_for_decoded_file_size():
    response=Response(body=b'decoded source bytes',headers={'Content-Length':'4','Content-Encoding':'gzip'})
    transport=ReadOnlyHttpsTransport((),session=HttpSession(response))
    assert transport.request('GET','/v1.0/drives/synthetic/items/file/content',headers={},body=None,timeout=30).body==b'decoded source bytes'


def test_invalid_pilot_month_is_rejected_before_any_auth_initialization(config,tmp_path,monkeypatch,capsys):
    from equipment_data_manager.m365_pilot import main
    path=tmp_path/'test.toml';path.write_text(config_text(config))
    monkeypatch.setattr(ReadOnlyTestPilot,'authorized',lambda *a,**k:pytest.fail('No SDK/auth initialization for invalid input'))
    assert main(['preview','--config',str(path),'--it-authorized-test-only','--output-root',str(tmp_path/'candidates'),
        '--report-type','service_orders','--item-id','item-1','--month','not-a-month'])==1
    assert json.loads(capsys.readouterr().out)['error']=='invalid_reporting_period'
    assert not config.cache_path.parent.exists()


def test_concurrent_refresh_cannot_resurrect_cache_after_local_signout(config):
    from concurrent.futures import ThreadPoolExecutor
    current=session(config);token=current.sign_in();current.clock=lambda:token.expires_at+60
    entered,release,signout_started,signout_done=Event(),Event(),Event(),Event()
    def refresh(*args,**kwargs):
        entered.set();assert release.wait(4)
        current.cache.deserialize('{"AccessToken":{"synthetic":{"secret":"SYNTHETIC_REFRESHED"}}}')
        current.cache.has_state_changed=True
        return current.client.result
    current.client.acquire_token_silent=refresh
    def logout():
        signout_started.set();current.sign_out();signout_done.set()
    with ThreadPoolExecutor(max_workers=2) as pool:
        refreshed=pool.submit(current.token)
        assert entered.wait(3)
        signed_out=pool.submit(logout)
        try:
            assert signout_started.wait(3) and not signout_done.wait(0.05)
        finally:release.set()
        assert refreshed.result(timeout=4).value=='SYNTHETIC_ACCESS_ONLY'
        signed_out.result(timeout=4)
    assert current.closed and json.loads(FakeProtector().unprotect(config.cache_path.read_bytes()))=={}
    with pytest.raises(StorageError,match='auth_signed_out'):current.token()
