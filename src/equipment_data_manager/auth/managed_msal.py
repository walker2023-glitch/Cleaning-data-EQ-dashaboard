"""Official MSAL bootstrap is guarded; imports/construction never occur at startup."""
import base64
import json
from pathlib import Path
import re
from uuid import UUID, uuid4

from equipment_data_manager.auth.msal_session import MsalSession
from equipment_data_manager.auth.token_cache import ProtectedTokenCache
from equipment_data_manager.m365_config import require_local
from equipment_data_manager.storage.contracts import StorageError
from equipment_data_manager.storage.https_transport import MsalHttpsClient,suppress_wire_logging


class CacheLease:
    """Exclusive whole-session lease prevents stale multi-process cache resurrection."""
    def __init__(self,path):
        self.path=Path(str(path)+'.session.lock');self.owner=uuid4().hex.encode();self.held=False

    def acquire(self):
        require_local(self.path.parent)
        if self.path.is_symlink():raise StorageError('auth_cache_busy')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        try:
            with self.path.open('xb') as stream:stream.write(self.owner)
            self.held=True
        except FileExistsError:raise StorageError('auth_cache_busy') from None
        except OSError:raise StorageError('auth_cache_unavailable') from None

    def release(self):
        if not self.held:return
        try:
            if self.path.is_symlink() or self.path.read_bytes()!=self.owner:
                raise StorageError('auth_cache_lease_lost')
            self.path.unlink();self.held=False
        except OSError:raise StorageError('auth_cache_cleanup_required') from None


class ManagedMsalSession(MsalSession):
    def __init__(self,config,client,cache,persistence,lease,http,**kwargs):
        super().__init__(config,client,interactive_enabled=True,**kwargs)
        self.cache,self.persistence,self.lease,self.http=cache,persistence,lease,http
        self._claims=None;self.closed=False
        self.connection_status='not_signed_in'

    def _accept(self,result,*,silent):
        if isinstance(result,dict) and result.get('error') in ('interaction_required','login_required','consent_required'):
            self.invalidate();self.connection_status='interaction_required'
            raise StorageError('auth_interaction_required')
        try:token=super()._accept(result,silent=silent)
        except StorageError:
            self.invalidate();self.connection_status='sign_in_failed';raise
        try:UUID(result['id_token_claims']['oid'])
        except (ValueError,KeyError,TypeError,AttributeError):
            self.invalidate();raise StorageError('auth_subject_invalid') from None
        self._claims=None
        self.connection_status='signed_in_resources_not_verified'
        return token

    def token(self):
        if self.closed:raise StorageError('auth_signed_out')
        if self._claims:raise StorageError('auth_interaction_required')
        try:return super().token()
        finally:self.persistence.save(self.cache)

    def sign_in(self):
        if self.closed:raise StorageError('auth_signed_out')
        try:
            result=self.client.acquire_token_interactive(scopes=list(self.config.scopes),prompt='select_account',
                timeout=120,claims_challenge=self._claims)
            token=self._accept(result,silent=False)
            oid=result['id_token_claims']['oid']
            matches=[a for a in self.client.get_accounts() if a.get('realm')==self.config.tenant_id and a.get('local_account_id')==oid]
            if len(matches)!=1:
                self.invalidate();raise StorageError('auth_account_selection_required')
            self.account_id=matches[0]['home_account_id']
            self._expired=False
            return token
        except StorageError:raise
        except Exception:
            self.invalidate();raise StorageError('auth_failed') from None
        finally:self.persistence.save(self.cache)

    def record_challenge(self,header):
        self.invalidate();self.connection_status='interaction_required'
        if not header:return
        try:
            if not isinstance(header,str) or len(header)>16384:raise ValueError
            matches=re.findall(r'\bclaims="([A-Za-z0-9_+/=-]+)"',header)
            if len(matches)!=1:raise ValueError
            raw=base64.b64decode(matches[0]+'='*((-len(matches[0]))%4),altchars=b'-_',validate=True)
            claims=json.loads(raw)
            if not isinstance(claims,dict) or not claims or len(raw)>8192:raise ValueError
            self._claims=json.dumps(claims,separators=(',',':'))
        except (ValueError,TypeError,UnicodeError):raise StorageError('auth_claims_challenge_invalid') from None

    def sign_out(self):
        """Local SDK/cache sign-out, not browser SSO logout or server token revocation."""
        self.invalidate();self.closed=True;self.connection_status='sign_out_incomplete'
        try:
            for account in self.client.get_accounts():self.client.remove_account(account)
        except Exception:
            # Still clear the entire dedicated application cache if SDK removal fails.
            pass
        try:
            self.cache.deserialize('{}');self.cache.has_state_changed=True
            self.persistence.save(self.cache)
            self.connection_status='signed_out_locally'
        except Exception:raise StorageError('auth_sign_out_incomplete') from None
        finally:
            try:self.http.close()
            finally:self.lease.release()

    def close(self):
        self.invalidate();self.closed=True;self.connection_status='closed_cache_retained'
        try:self.persistence.save(self.cache)
        finally:
            try:self.http.close()
            finally:self.lease.release()


def create_session(config,*,operator_authorized=False,client_factory=None,cache_factory=None,
                   protector=None,http=None):
    """Calling the REAL factory can contact Microsoft discovery. Requires IT gate.

    Injected factories/protectors are for offline tests; runtime has no plaintext
    fallback. Real configuration/policy is trusted operator input, not business authority.
    """
    config.authorize(operator_authorized=operator_authorized)
    suppress_wire_logging()
    try:
        import msal
    except ImportError:raise StorageError('m365_dependencies_missing') from None
    persistence=ProtectedTokenCache(config.cache_path,protector=protector)
    lease=CacheLease(config.cache_path)
    lease.acquire()
    try:
        http=http if http is not None else MsalHttpsClient(tenant_id=config.organization.tenant_id)
        cache=(cache_factory or msal.SerializableTokenCache)()
        persistence.load_into(cache)
        client=(client_factory or msal.PublicClientApplication)(config.organization.client_id,
            authority='https://login.microsoftonline.com/'+config.organization.tenant_id,
            token_cache=cache,http_client=http,instance_discovery=False,enable_pii_log=False,
            client_capabilities=['CP1'],enable_broker_on_windows=False,
            enable_broker_on_mac=False,enable_broker_on_linux=False)
        return ManagedMsalSession(config.organization,client,cache,persistence,lease,http)
    except StorageError:
        if http is not None:http.close()
        lease.release();raise
    except Exception:
        if http is not None:http.close()
        lease.release();raise StorageError('auth_initialization_failed') from None
    except BaseException:
        try:
            if http is not None:http.close()
        finally:lease.release()
        raise

