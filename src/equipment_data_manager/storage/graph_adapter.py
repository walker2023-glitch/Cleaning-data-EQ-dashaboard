"""Injected Graph operations only: no HTTP implementation or live bootstrap.

The default GraphSharePointRepository remains disabled. This adapter is exercised
with synthetic fake sessions/transports; endpoint/tenant policies need live testing.
"""
from dataclasses import dataclass, field
from datetime import timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
import math
import re
import time
from typing import Protocol
from urllib.parse import quote, urlsplit

from equipment_data_manager.storage.contracts import FileRead, StorageError, StorageFile

PROBE_CONTENT = b'Equipment Data Manager synthetic connectivity probe only.\n'


@dataclass(frozen=True, repr=False)
class GraphResponse:
    status: int
    payload: dict | None = field(default=None,repr=False)
    body: bytes = field(default=b'',repr=False)
    headers: dict = field(default_factory=dict,repr=False)


class GraphTransport(Protocol):
    def request(self, method, target, *, headers, body, timeout):
        """Return GraphResponse; MUST NOT automatically follow redirects.

        No implementation ships here. Authorized bootstrap must enforce HTTPS,
        TLS verification, timeouts, bounded response size and redacted diagnostics.
        """
        ...


@dataclass(frozen=True, repr=False)
class GraphScope:
    site_id: str
    drive_id: str
    raw_folder_ids: tuple[str, ...]
    probe_folder_id: str | None = None
    download_hosts: tuple[str, ...] = ()

    def __post_init__(self):
        if (type(self.raw_folder_ids) is not tuple or type(self.download_hosts) is not tuple
                or not self.site_id or not self.drive_id or not self.raw_folder_ids
                or any(not isinstance(s,str) or not s or any(ord(c)<32 for c in s)
                       for s in (self.site_id,self.drive_id,*self.raw_folder_ids))
                or (self.probe_folder_id is not None and (not isinstance(self.probe_folder_id,str)
                    or not self.probe_folder_id or any(ord(c)<32 for c in self.probe_folder_id)))
                or self.probe_folder_id in self.raw_folder_ids
                or any(not isinstance(h,str) or not re.fullmatch(r'[a-z0-9.-]+',h) for h in self.download_hosts)):
            raise StorageError('graph_scope_invalid')


def _header(response, name):
    values=[value for key,value in response.headers.items() if key.casefold()==name.casefold()]
    if len(values)>1 and any(value!=values[0] for value in values):
        raise StorageError('graph_response_invalid')
    return values[0] if values else None


class OfflineGraphAdapter:
    """Read selected raw folders; only fixed synthetic .txt probes can be uploaded."""
    def __init__(self, scope, session, transport, *, attempts=3, max_bytes=64*1024*1024,
                 timeout=30, max_retry_delay=5, sleeper=time.sleep, clock=time.time):
        if not 1 <= attempts <= 5 or max_bytes <= 0 or timeout <= 0 or max_retry_delay < 0:
            raise StorageError('graph_policy_invalid')
        self.scope,self.session,self.transport = scope,session,transport
        self.attempts,self.max_bytes,self.timeout = attempts,max_bytes,timeout
        self.max_retry_delay,self.sleeper,self.clock = max_retry_delay,sleeper,clock

    def _delay(self, response, attempt):
        value = _header(response,'Retry-After') if response is not None else None
        if value is None:delay = 0.25 * 2**attempt
        else:
            try:delay = float(value)
            except (ValueError,TypeError):
                try:
                    parsed = parsedate_to_datetime(value)
                    if parsed.tzinfo is None:parsed = parsed.replace(tzinfo=timezone.utc)
                    delay = max(0,parsed.timestamp()-self.clock())
                except Exception:raise StorageError('storage_retry_later') from None
        # Never shorten the server's requested wait; defer instead of retrying early.
        if not math.isfinite(delay) or delay < 0 or delay > self.max_retry_delay:
            raise StorageError('storage_retry_later')
        self.sleeper(delay)

    def _request(self, method, target, *, body=None, missing='storage_file_missing', authenticated=True):
        for attempt in range(self.attempts if method=='GET' else 1):
            try:
                headers = {'Authorization':'Bearer '+self.session.token().value} if authenticated else {}
            except StorageError:raise
            except Exception:raise StorageError('auth_failed') from None
            if method=='PUT':headers.update({'If-None-Match':'*','Content-Type':'text/plain'})
            response = None
            try:
                response = self.transport.request(method,target,headers=headers,body=body,timeout=self.timeout)
            except (OSError,TimeoutError):
                if method!='GET':raise StorageError('storage_upload_outcome_unknown') from None
                if attempt+1==self.attempts:raise StorageError('storage_network_interrupted') from None
                self._delay(None,attempt);continue
            except StorageError:raise
            except Exception:
                raise StorageError('storage_transport_failed') from None
            if (not isinstance(response,GraphResponse) or type(response.status) is not int
                    or not isinstance(response.headers,dict) or any(not isinstance(k,str) for k in response.headers)):
                raise StorageError('graph_response_invalid')
            status = response.status
            if status==401:
                if not authenticated:raise StorageError('storage_download_link_expired')
                self.session.invalidate();raise StorageError('auth_session_expired')
            if status==403:raise StorageError('storage_access_denied')
            if status==404:raise StorageError(missing)
            if status in (409,412):raise StorageError('storage_conflict')
            if status in (429,503):
                if method!='GET':raise StorageError('storage_retry_later')
                if attempt+1==self.attempts:raise StorageError('storage_retry_exhausted')
                self._delay(response,attempt);continue
            if status not in (200,201,302,307):raise StorageError('graph_request_failed')
            return response
        raise StorageError('storage_retry_exhausted')

    @staticmethod
    def _payload(response):
        if response.status not in (200,201) or not isinstance(response.payload,dict):
            raise StorageError('graph_response_invalid')
        return response.payload

    def _pages(self, endpoint, *, missing='storage_folder_missing'):
        target, seen, identifiers, result = endpoint,set(),set(),[]
        for _ in range(100):
            if target in seen:raise StorageError('graph_pagination_rejected')
            seen.add(target)
            payload = self._payload(self._request('GET',target,missing=missing))
            if not isinstance(payload.get('value'),list):raise StorageError('graph_response_invalid')
            for item in payload['value']:
                if not isinstance(item,dict) or not isinstance(item.get('id'),str) or not item['id'] or item['id'] in identifiers:
                    raise StorageError('graph_listing_identity_rejected')
                identifiers.add(item['id']);result.append(item)
                if len(result)>10000:raise StorageError('graph_listing_limit')
            link = payload.get('@odata.nextLink')
            if not link:return result
            try:
                parsed = urlsplit(link)
                if parsed.scheme!='https' or parsed.netloc!='graph.microsoft.com' or parsed.path!=endpoint or parsed.fragment:
                    raise ValueError
                target = parsed.path + ('?'+parsed.query if parsed.query else '')
            except (ValueError,TypeError):raise StorageError('graph_pagination_rejected') from None
        raise StorageError('graph_listing_limit')

    def site(self):
        data = self._payload(self._request('GET','/v1.0/sites/'+quote(self.scope.site_id,safe=''),missing='graph_site_missing'))
        if data.get('id')!=self.scope.site_id:raise StorageError('graph_scope_mismatch')
        return {'id':data['id'],'name':data.get('displayName','')}

    def libraries(self):
        return tuple({'id':i['id'],'name':i.get('name','')} for i in self._pages(
            '/v1.0/sites/'+quote(self.scope.site_id,safe='')+'/drives',missing='graph_site_missing')
            if i.get('driveType')=='documentLibrary')

    def _folder_endpoint(self, folder):
        return '/v1.0/drives/'+quote(self.scope.drive_id,safe='')+'/items/'+quote(folder,safe='')+'/children'

    def _entry(self, item, parent):
        try:
            p = item['parentReference']
            if (not isinstance(item['id'],str) or not item['id']
                    or not isinstance(item['name'],str) or not item['name'] or '/' in item['name'] or '\\' in item['name']
                    or type(item['size']) is not int or item['size']<0 or not isinstance(item['eTag'],str) or not item['eTag']
                    or p['driveId']!=self.scope.drive_id or p['id']!=parent or 'remoteItem' in item
                    or not isinstance(item.get('file'),dict)):
                raise ValueError
            digest = item['file'].get('hashes',{}).get('sha256Hash')
            if digest is not None and not re.fullmatch(r'[a-fA-F0-9]{64}',digest):raise ValueError
            return StorageFile('graph',self.scope.drive_id,parent,item['id'],item['name'],item['size'],item['eTag'],
                               digest.lower() if digest else None)
        except (KeyError,ValueError,TypeError,AttributeError):raise StorageError('graph_file_metadata_rejected') from None

    def _list(self, folder):
        files=[]
        for item in self._pages(self._folder_endpoint(folder)):
            if 'folder' in item:continue
            if not isinstance(item.get('name'),str):raise StorageError('graph_file_metadata_rejected')
            if item['name'].startswith(('.', '~')):continue
            files.append(self._entry(item,folder))
        return tuple(files)

    def list_files(self, folder_id):
        if folder_id not in self.scope.raw_folder_ids:raise StorageError('graph_folder_not_authorized')
        return self._list(folder_id)

    def _metadata(self, source):
        path='/v1.0/drives/'+quote(self.scope.drive_id,safe='')+'/items/'+quote(source.item_id,safe='')
        entry=self._entry(self._payload(self._request('GET',path)),source.parent_id)
        if entry!=source:raise StorageError('storage_source_changed')
        return path

    def _read(self, source, expected_sha256):
        if source.size_bytes>self.max_bytes:raise StorageError('storage_file_too_large')
        path=self._metadata(source)
        response=self._request('GET',path+'/content')
        if response.status in (302,307):
            location=_header(response,'Location') or ''
            try:
                link=urlsplit(location)
                if (link.scheme!='https' or link.netloc not in self.scope.download_hosts
                        or link.username or link.password or link.fragment):raise ValueError
            except (ValueError,TypeError):raise StorageError('graph_download_redirect_rejected') from None
            # NEVER forward the bearer token to the content host.
            response=self._request('GET',location,authenticated=False)
        if response.status!=200 or not isinstance(response.body,bytes) or len(response.body)!=source.size_bytes:
            raise StorageError('storage_download_incomplete')
        digest=sha256(response.body).hexdigest()
        if (expected_sha256 and digest!=expected_sha256) or (source.sha256 and digest!=source.sha256):
            raise StorageError('storage_source_hash_mismatch')
        self._metadata(source)
        return FileRead(response.body,digest,source.version,
            'expected_sha256_matched_version_checked' if expected_sha256 or source.sha256 else 'hash_computed_version_checked')

    def read(self, source, *, expected_sha256=None):
        if (source.provider!='graph' or source.container!=self.scope.drive_id or source.parent_id not in self.scope.raw_folder_ids):
            raise StorageError('storage_reference_rejected')
        return self._read(source,expected_sha256)

    def probe_files(self):
        if not self.scope.probe_folder_id:raise StorageError('graph_probe_not_configured')
        return self._list(self.scope.probe_folder_id)

    def verify_probe(self, source):
        if (not self.scope.probe_folder_id or source.provider!='graph' or source.container!=self.scope.drive_id
                or source.parent_id!=self.scope.probe_folder_id):raise StorageError('graph_probe_not_configured')
        return self._read(source,sha256(PROBE_CONTENT).hexdigest())

    def upload_probe(self, name):
        if not self.scope.probe_folder_id:raise StorageError('graph_probe_not_configured')
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,60}\.txt',name):
            raise StorageError('graph_probe_name_rejected')
        path='/v1.0/drives/'+quote(self.scope.drive_id,safe='')+'/items/'+quote(self.scope.probe_folder_id,safe='')
        response=self._request('PUT',path+':/'+quote(name,safe='')+':/content?@microsoft.graph.conflictBehavior=fail',body=PROBE_CONTENT)
        entry=self._entry(self._payload(response),self.scope.probe_folder_id)
        if entry.name!=name or entry.size_bytes!=len(PROBE_CONTENT):raise StorageError('storage_upload_verification_failed')
        self.verify_probe(entry)
        return entry

    def create_output(self, *args, **kwargs):
        raise StorageError('publication_not_implemented')
