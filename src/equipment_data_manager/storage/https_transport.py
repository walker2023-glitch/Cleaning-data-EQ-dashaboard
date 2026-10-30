"""Bounded TLS-verified HTTPS adapters. No URLs, headers or bodies in diagnostics."""
import json
import logging
from urllib.parse import urlsplit
from equipment_data_manager.storage.contracts import StorageError
from equipment_data_manager.storage.graph_adapter import GraphResponse


def suppress_wire_logging():
    # SDK/HTTP debug and error paths can include signed URLs or response bodies.
    # Application diagnostics use safe category/status strings instead.
    prefixes=('msal','requests','urllib3')
    names=set(prefixes)|{name for name in logging.Logger.manager.loggerDict
        if any(name.startswith(prefix+'.') for prefix in prefixes)}
    for name in names:
        logger=logging.getLogger(name)
        logger.handlers=[logging.NullHandler()]
        logger.propagate=False


def requests_session():
    try:
        import requests
        session=requests.Session()
        session.headers.clear()  # Never retain a bearer or other application header.
        return session
    except ImportError:
        raise StorageError('m365_dependencies_missing') from None


class NoNetrcAuth:
    def __call__(self, request):return request


class ReadOnlyHttpsTransport:
    def __init__(self, download_hosts, *, session=None, max_bytes=64*1024*1024):
        suppress_wire_logging()
        self.download_hosts=frozenset(download_hosts)
        self.session=session if session is not None else requests_session()
        self.max_bytes=max_bytes
        self.last_diagnostic='not_contacted'

    def request(self,method,target,*,headers,body,timeout):
        if method!='GET' or body is not None:raise StorageError('m365_read_only')
        if not isinstance(timeout,(float,int)) or not 0<timeout<=60:raise StorageError('m365_timeout_policy_invalid')
        try:
            url='https://graph.microsoft.com'+target if target.startswith('/v1.0/') else target
            parsed=urlsplit(url)
            if (parsed.scheme!='https' or parsed.username or parsed.password or parsed.fragment
                    or parsed.netloc!=parsed.hostname or parsed.hostname not in {'graph.microsoft.com',*self.download_hosts}
                    or any(ord(c)<32 for c in url) or '\\' in url):raise ValueError
            if parsed.hostname=='graph.microsoft.com':
                if not parsed.path.startswith('/v1.0/'):raise ValueError
            elif headers:raise ValueError  # CDN gets neither bearer nor other application headers.
            if set(headers)-{'Authorization'}:raise ValueError
        except (ValueError,TypeError,AttributeError):raise StorageError('m365_https_target_rejected') from None
        response=None
        try:
            response=self.session.request('GET',url,headers=dict(headers),auth=NoNetrcAuth(),
                allow_redirects=False,timeout=(min(10,timeout),timeout),verify=True,stream=True)
            status=response.status_code
            kept={key:value for key,value in response.headers.items()
                  if key.casefold() in ('location','retry-after','www-authenticate','content-length','content-type')}
            # Error/redirect bodies may contain tokens, descriptions or private paths.
            raw=b''
            if status==200:
                size=0;chunks=[]
                length=response.headers.get('Content-Length')
                if length is not None and (not length.isdecimal() or int(length)>self.max_bytes):
                    raise StorageError('storage_file_too_large')
                for chunk in response.iter_content(chunk_size=64*1024):
                    size+=len(chunk)
                    if size>self.max_bytes:raise StorageError('storage_file_too_large')
                    chunks.append(chunk)
                raw=b''.join(chunks)
                # Content-Length describes wire bytes; requests decodes Content-Encoding.
                # File metadata/hash checks still verify the exact decoded source bytes.
                if (length is not None and response.headers.get('Content-Encoding','identity').casefold() in ('','identity')
                        and len(raw)!=int(length)):raise OSError('download_interrupted')
            payload=None
            if status==200 and parsed.hostname=='graph.microsoft.com' and 'json' in response.headers.get('Content-Type','').lower():
                try:payload=json.loads(raw)
                except (ValueError,UnicodeError):raise StorageError('graph_response_invalid') from None
            self.last_diagnostic='http_'+str(status)
            return GraphResponse(status,payload,raw,kept)
        except StorageError:
            self.last_diagnostic='transport_policy_or_integrity_failure';raise
        except Exception:
            self.last_diagnostic='network_or_tls_failure'
            raise OSError('m365_network_or_tls_failure') from None
        finally:
            if response is not None:response.close()

    def close(self):self.session.close()


class MsalHttpsClient:
    """MSAL-compatible GET/POST client, exact organizational authority host only.

    MSAL owns OAuth/PKCE/loopback and browser MFA. No redirects or TLS bypass here.
    Environment enterprise proxies/CA settings remain supported by requests.
    """
    def __init__(self, *, session=None, tenant_id=None):
        suppress_wire_logging()
        self.tenant_id=tenant_id
        self.session=session if session is not None else requests_session()

    def _call(self,method,url,**kwargs):
        parsed=urlsplit(url)
        if (parsed.scheme!='https' or parsed.netloc!='login.microsoftonline.com' or parsed.fragment
                or (self.tenant_id is not None and not parsed.path.casefold().startswith('/'+self.tenant_id+'/'))
                or any(ord(c)<32 for c in url) or '\\' in url):raise StorageError('auth_authority_rejected')
        if set(kwargs)-{'params','data','headers','timeout'}:raise StorageError('auth_http_policy_rejected')
        kwargs.pop('timeout',None)
        try:
            response=self.session.request(method,url,**kwargs,auth=NoNetrcAuth(),allow_redirects=False,
                timeout=(10,30),verify=True,stream=True)
            if response.status_code in (301,302,303,307,308):
                response.close();raise StorageError('auth_authority_redirect_rejected')
            # Bound and validate before MSAL can log malformed response text.
            chunks=[];size=0
            try:
                for chunk in response.iter_content(chunk_size=64*1024):
                    size+=len(chunk)
                    if size>2*1024*1024:raise StorageError('auth_response_invalid')
                    chunks.append(chunk)
                raw=b''.join(chunks)
                payload=json.loads(raw)
                if not isinstance(payload,dict):raise ValueError
                for key in ('authorization_endpoint','token_endpoint'):
                    if key in payload:
                        endpoint=urlsplit(payload[key])
                        if (endpoint.scheme!='https' or endpoint.netloc!='login.microsoftonline.com'
                                or (self.tenant_id is not None and not endpoint.path.casefold().startswith('/'+self.tenant_id+'/'))):
                            raise StorageError('auth_authority_rejected')
                response._content=raw  # Requests response retains bounded bytes for MSAL.
                response._content_consumed=True
            except StorageError:raise
            except Exception:raise StorageError('auth_response_invalid') from None
            finally:response.close()
            return response
        except StorageError:raise
        except Exception:raise StorageError('auth_network_failed') from None

    def get(self,url,**kwargs):return self._call('GET',url,**kwargs)
    def post(self,url,**kwargs):return self._call('POST',url,**kwargs)
    def close(self):self.session.close()
