"""MSAL PublicClientApplication-compatible session, tested with injected fakes.

No MSAL import, authority discovery, credentials, browser or HTTP construction.
A live SDK bootstrap/wiring needs a separately authorized IT test pilot.
"""
from dataclasses import dataclass, field
import re
import time
from uuid import UUID
from equipment_data_manager.storage.contracts import StorageError


@dataclass(frozen=True)
class OrganizationalConfig:
    tenant_id: str
    client_id: str
    scopes: tuple[str, ...]

    def __post_init__(self):
        try:
            object.__setattr__(self, 'tenant_id', str(UUID(self.tenant_id)))
            object.__setattr__(self, 'client_id', str(UUID(self.client_id)))
        except (ValueError, TypeError, AttributeError):
            raise StorageError('auth_configuration_invalid') from None
        if not self.scopes or any(not isinstance(s,str) or not s.strip() or any(c.isspace() for c in s) for s in self.scopes):
            raise StorageError('auth_configuration_invalid')


@dataclass(frozen=True, repr=False)
class AccessToken:
    value: str = field(repr=False)
    expires_at: float


class MsalSession:
    def __init__(self, config, client, *, account_id=None, interactive_enabled=False, clock=time.time):
        self.config, self.client, self.account_id = config, client, account_id
        self.interactive_enabled, self.clock = interactive_enabled, clock
        self._token = None
        self._expired = False

    def invalidate(self):
        self._token = None
        self._expired = True

    def _accept(self, result, *, silent):
        if not isinstance(result,dict) or not result.get('access_token'):
            error = result.get('error') if isinstance(result,dict) else None
            code = ('auth_permission_denied' if error == 'access_denied' else
                    'auth_session_expired' if silent else 'auth_failed')
            raise StorageError(code) from None
        claims = result.get('id_token_claims')
        if not isinstance(claims,dict) or claims.get('tid') != self.config.tenant_id:
            raise StorageError('auth_wrong_tenant')
        value = result['access_token']
        try:
            expires = float(result['expires_on']) if 'expires_on' in result else self.clock() + float(result['expires_in'])
            if not re.fullmatch(r'[A-Za-z0-9._~+/=-]+', value) or not self.clock() + 30 < expires < float('inf'):
                raise ValueError
        except (ValueError, TypeError, KeyError):
            raise StorageError('auth_invalid_token_result') from None
        self._token, self._expired = AccessToken(value, expires), False
        return self._token

    def token(self):
        if self._expired:
            raise StorageError('auth_session_expired')
        if self._token is not None and self._token.expires_at > self.clock() + 30:
            return self._token
        try:
            accounts = [a for a in self.client.get_accounts() if a.get('realm') == self.config.tenant_id]
            if self.account_id:
                accounts = [a for a in accounts if a.get('home_account_id') == self.account_id]
            if len(accounts) != 1:
                raise StorageError('auth_account_selection_required')
            result = self.client.acquire_token_silent(list(self.config.scopes), account=accounts[0])
        except StorageError:
            raise
        except Exception:
            raise StorageError('auth_failed') from None
        return self._accept(result, silent=True)

    def sign_in(self):
        if not self.interactive_enabled:
            raise StorageError('auth_interactive_not_enabled')
        try:
            result = self.client.acquire_token_interactive(scopes=list(self.config.scopes), prompt='select_account')
        except Exception:
            raise StorageError('auth_failed') from None
        return self._accept(result, silent=False)
