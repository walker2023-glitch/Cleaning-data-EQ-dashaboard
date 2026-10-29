"""Offline Graph-to-real-engine preview using an in-memory transport, never HTTP."""
import argparse
from importlib.resources import files
import json
from pathlib import Path

from equipment_data_manager.auth.msal_session import MsalSession, OrganizationalConfig
from equipment_data_manager.processing.models import ProcessingRequest
from equipment_data_manager.processing.repair_financial import powerbi_coordinator
from equipment_data_manager.storage.graph_adapter import GraphScope, GraphResponse, OfflineGraphAdapter

TENANT='11111111-1111-1111-1111-111111111111'


class SyntheticPublicClient:
    def get_accounts(self):return [{'realm':TENANT,'home_account_id':'synthetic-account'}]
    def acquire_token_silent(self,scopes,*,account):
        return {'access_token':'SYNTHETIC_OFFLINE_ONLY','expires_in':3600,'id_token_claims':{'tid':TENANT}}


class InMemoryTransport:
    def __init__(self,raw):
        self.raw=raw
        self.item=dict(id='synthetic-item',name='service.csv',size=len(raw),eTag='"synthetic-v1"',file={},
            parentReference={'driveId':'synthetic-drive','id':'synthetic-raw'})
    def request(self,method,target,*,headers,body,timeout):
        if method!='GET':raise AssertionError('Demo never writes')
        if target.endswith('/children'):return GraphResponse(200,{'value':[self.item]})
        if target.endswith('/content'):return GraphResponse(200,body=self.raw)
        return GraphResponse(200,self.item)


def preview(output_root):
    if output_root.exists():raise ValueError('Choose a new preview directory')
    raw=files('equipment_data_manager').joinpath('resources/samples/service_sample.csv').read_bytes()
    config=OrganizationalConfig(TENANT,'22222222-2222-2222-2222-222222222222',('Files.Read',))
    session=MsalSession(config,SyntheticPublicClient())
    adapter=OfflineGraphAdapter(GraphScope('synthetic-site','synthetic-drive',('synthetic-raw',)),
                                session,InMemoryTransport(raw))
    source,=adapter.list_files('synthetic-raw');download=adapter.read(source)
    result=powerbi_coordinator(output_root).preview(ProcessingRequest('service_orders','2026-09',
        raw_bytes=download.content,source_name=source.name))
    assert result.status=='success'
    assert not output_root.exists()
    return dict(mode='mock_graph',transport='in_memory_only',live_authentication=False,
        publication_enabled=False,sync_verified=False,source_sha256=download.sha256,
        preview_status=result.status.value,input_rows=result.input_rows,output_rows=result.output_rows,
        outputs_written=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview-root',type=Path,default=Path('data/offline-graph-preview'))
    args=parser.parse_args()
    print(json.dumps(preview(args.preview_root),indent=2))
