"""Fake MSAL sessions and synthetic protected-cache bytes only; no sign-in/network."""
import os
from pathlib import Path
import sys

import pytest

from equipment_data_manager.auth.msal_session import MsalSession, OrganizationalConfig
from equipment_data_manager.auth.token_cache import ProtectedTokenCache, WindowsDpapiProtector
from equipment_data_manager.storage.contracts import StorageError

TENANT='11111111-1111-1111-1111-111111111111'
CLIENT='22222222-2222-2222-2222-222222222222'
CONFIG=OrganizationalConfig(TENANT,CLIENT,('Files.Read',))


class FakeMsal:
    def __init__(self):
        self.accounts=[{'realm':TENANT,'home_account_id':'synthetic-account'}]
        self.result={'access_token':'SYNTHETIC_TOKEN_ONLY','expires_in':3600,'id_token_claims':{'tid':TENANT}}
        self.silent_calls,self.interactive_calls=0,0
    def get_accounts(self):return self.accounts
    def acquire_token_silent(self,scopes,*,account):
        self.silent_calls+=1;return self.result
    def acquire_token_interactive(self,**kwargs):
        self.interactive_calls+=1;return self.result


def test_cached_token_expiry_and_explicit_interactive_gate():
    client=FakeMsal();now=[100]
    session=MsalSession(CONFIG,client,clock=lambda:now[0])
    token=session.token();assert token.value=='SYNTHETIC_TOKEN_ONLY' and 'SYNTHETIC_TOKEN' not in repr(token)
    assert session.token() is token and client.silent_calls==1
    with pytest.raises(StorageError,match='interactive_not_enabled'):session.sign_in()
    assert client.interactive_calls==0
    now[0]=4000;client.result={'error':'interaction_required','error_description':'PRIVATE SDK MESSAGE'}
    with pytest.raises(StorageError,match='session_expired') as error:session.token()
    assert 'PRIVATE' not in str(error.value)
    interactive=MsalSession(CONFIG,client,interactive_enabled=True,clock=lambda:100)
    client.result=FakeMsal().result
    assert interactive.sign_in().value=='SYNTHETIC_TOKEN_ONLY' and client.interactive_calls==1


@pytest.mark.parametrize('result,code', [
    ({'error':'access_denied'},'auth_permission_denied'),({},'auth_session_expired'),
    ({'access_token':'SYNTHETIC','expires_in':3600,'id_token_claims':{'tid':'different'}},'auth_wrong_tenant'),
    ({'access_token':'unsafe\r\nheader','expires_in':3600,'id_token_claims':{'tid':TENANT}},'auth_invalid_token_result'),
    ({'access_token':'synthetic','expires_in':0,'id_token_claims':{'tid':TENANT}},'auth_invalid_token_result'),
])
def test_failed_expired_wrong_tenant_or_malformed_auth_is_not_accepted(result,code):
    client=FakeMsal();client.result=result
    with pytest.raises(StorageError,match=code):MsalSession(CONFIG,client,clock=lambda:100).token()


def test_account_selection_is_explicit_and_http_expiry_requires_reauth():
    client=FakeMsal();client.accounts*=2
    with pytest.raises(StorageError,match='account_selection_required'):MsalSession(CONFIG,client).token()
    client=FakeMsal();session=MsalSession(CONFIG,client,clock=lambda:100);session.token();session.invalidate()
    with pytest.raises(StorageError,match='session_expired'):session.token()
    assert client.silent_calls==1
    with pytest.raises(StorageError):OrganizationalConfig('common',CLIENT,('Files.Read',))
    with pytest.raises(StorageError):OrganizationalConfig(TENANT,CLIENT,())


class FakeProtector:
    # TEST ONLY: proves staging discipline, not real cryptography.
    def protect(self,raw):return bytes(c^0xA5 for c in raw)
    def unprotect(self,raw):return self.protect(raw)


class FakeCache:
    has_state_changed=True
    text='SYNTHETIC_SERIALIZED_CACHE_ONLY'
    def serialize(self):return self.text
    def deserialize(self,text):self.text=text


def test_cache_stages_only_protected_bytes_and_restores_without_plaintext_file(tmp_path):
    path=tmp_path/'private/cache.bin';store=ProtectedTokenCache(path,protector=FakeProtector())
    cache=FakeCache();store.save(cache)
    assert cache.text.encode() not in path.read_bytes()
    assert list(path.parent.iterdir())==[path]
    restored=FakeCache();restored.text='';store.load_into(restored)
    assert restored.text==cache.text
    unchanged=path.read_bytes();cache.has_state_changed=False;store.save(cache)
    assert path.read_bytes()==unchanged


def test_cache_write_failure_preserves_old_blob_and_does_not_remove_foreign_lock(tmp_path,monkeypatch):
    path=tmp_path/'cache.bin';store=ProtectedTokenCache(path,protector=FakeProtector());cache=FakeCache();store.save(cache)
    original=path.read_bytes()
    def fail(*args):raise OSError('PRIVATE DISK MESSAGE')
    monkeypatch.setattr(os,'replace',fail)
    cache.text='SYNTHETIC_NEW_CACHE'
    with pytest.raises(StorageError):store.save(cache)
    assert path.read_bytes()==original and list(tmp_path.iterdir())==[path]
    lock=path.with_name(path.name+'.lock');lock.write_bytes(b'other writer')
    with pytest.raises(StorageError,match='cache_busy'):store.save(cache)
    assert lock.read_bytes()==b'other writer'


def test_cache_requires_local_protection_and_corrupt_cache_does_not_become_plaintext(tmp_path,monkeypatch):
    import equipment_data_manager.settings as settings
    monkeypatch.setattr(settings,'candidate_location_error',lambda p:'synced')
    with pytest.raises(StorageError,match='requires_local_disk'):ProtectedTokenCache(tmp_path/'cache',protector=FakeProtector())
    monkeypatch.setattr(settings,'candidate_location_error',lambda p:'')
    if sys.platform=='win32':
        protector=WindowsDpapiProtector();raw=b'SYNTHETIC_DPAPI_CACHE_ONLY'
        encrypted=protector.protect(raw)
        assert raw not in encrypted and protector.unprotect(encrypted)==raw
        with pytest.raises(StorageError):protector.unprotect(b'corrupt synthetic blob')
    else:
        with pytest.raises(StorageError,match='protection_unavailable'):WindowsDpapiProtector()


def test_cache_failure_preserves_dirty_state_even_when_sdk_serialize_clears_it(tmp_path,monkeypatch):
    class SdkLikeCache(FakeCache):
        def serialize(self):self.has_state_changed=False;return self.text
    store=ProtectedTokenCache(tmp_path/'cache.bin',protector=FakeProtector());cache=SdkLikeCache()
    original=os.replace
    monkeypatch.setattr(os,'replace',lambda *a:(_ for _ in ()).throw(OSError('synthetic write failure')))
    with pytest.raises(StorageError):store.save(cache)
    assert cache.has_state_changed is True
    monkeypatch.setattr(os,'replace',original);store.save(cache)
    assert (tmp_path/'cache.bin').exists()


def test_cache_rechecks_local_policy_before_use_not_only_construction(tmp_path,monkeypatch):
    import equipment_data_manager.settings as settings
    store=ProtectedTokenCache(tmp_path/'cache.bin',protector=FakeProtector())
    monkeypatch.setattr(settings,'candidate_location_error',lambda p:'now synchronized')
    with pytest.raises(StorageError,match='requires_local_disk'):store.save(FakeCache())
    assert not (tmp_path/'cache.bin').exists()
