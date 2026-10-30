"""Read-only profile of the existing Graph adapter; all writes fail before token use."""
from equipment_data_manager.storage.contracts import StorageError
from equipment_data_manager.storage.graph_adapter import OfflineGraphAdapter, _header


class ChallengeTransport:
    def __init__(self,transport,session):self.transport,self.session=transport,session
    def request(self,method,target,*,headers,body,timeout):
        if method!='GET' or body is not None:raise StorageError('m365_read_only')
        result=self.transport.request(method,target,headers=headers,body=body,timeout=timeout)
        if result.status==401 and headers.get('Authorization'):
            self.session.invalidate()
            self.session.record_challenge(_header(result,'WWW-Authenticate'))
        return result


class ReadOnlyGraphAdapter(OfflineGraphAdapter):
    def __init__(self,scope,session,transport,**kwargs):
        if scope.probe_folder_id is not None:raise StorageError('m365_read_only')
        super().__init__(scope,session,ChallengeTransport(transport,session),**kwargs)

    def upload_probe(self,*args,**kwargs):raise StorageError('m365_read_only')
    def probe_files(self,*args,**kwargs):raise StorageError('m365_read_only')
    def verify_probe(self,*args,**kwargs):raise StorageError('m365_read_only')
    def create_output(self,*args,**kwargs):raise StorageError('m365_read_only')
