"""DPAPI user-protected serialized cache; plaintext is never staged on disk.

No cache is automatically created or attached to the desktop. Live MSAL bootstrap,
IT ACL/retention validation and lifecycle wiring remain a separate pilot gate.
"""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import sys
from uuid import uuid4
from equipment_data_manager.storage.contracts import StorageError


class WindowsDpapiProtector:
    def __init__(self):
        if sys.platform != 'win32':
            raise StorageError('auth_protection_unavailable')

    def _transform(self, raw, decrypt):
        class Blob(ctypes.Structure):
            _fields_ = [('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_ubyte))]
        buffer = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
        source, target = Blob(len(raw), buffer), Blob()
        crypto = ctypes.WinDLL('crypt32',use_last_error=True)
        kernel = ctypes.WinDLL('kernel32',use_last_error=True)
        function = crypto.CryptUnprotectData if decrypt else crypto.CryptProtectData
        function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                             ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        function.restype = wintypes.BOOL
        kernel.LocalFree.argtypes = [ctypes.c_void_p]; kernel.LocalFree.restype = ctypes.c_void_p
        # UI_FORBIDDEN; no LOCAL_MACHINE flag: current Windows user protection.
        if not function(ctypes.byref(source),None,None,None,None,1,ctypes.byref(target)):
            raise StorageError('auth_cache_protection_failed')
        try:
            return ctypes.string_at(target.pbData,target.cbData)
        finally:
            kernel.LocalFree(ctypes.cast(target.pbData,ctypes.c_void_p))

    def protect(self, raw): return self._transform(raw,False)
    def unprotect(self, raw): return self._transform(raw,True)


class ProtectedTokenCache:
    def __init__(self, path: Path, *, protector=None):
        from equipment_data_manager.settings import candidate_location_error
        self.path = Path(path).absolute()
        if (candidate_location_error(self.path.parent) or any(p.is_symlink() or p.is_junction()
                for p in (self.path,*self.path.parents))):
            raise StorageError('auth_cache_requires_local_disk')
        self.protector = protector if protector is not None else WindowsDpapiProtector()

    def _check_local(self):
        from equipment_data_manager.settings import candidate_location_error
        if candidate_location_error(self.path.parent) or any(p.is_symlink() or p.is_junction()
                for p in (self.path,*self.path.parents)):
            raise StorageError('auth_cache_requires_local_disk')

    def load_into(self, serialized_cache):
        self._check_local()
        try:
            if self.path.is_symlink():raise StorageError('auth_cache_unavailable')
            encrypted = self.path.read_bytes()
        except FileNotFoundError:
            return
        except OSError:
            raise StorageError('auth_cache_unavailable') from None
        try:
            serialized_cache.deserialize(self.protector.unprotect(encrypted).decode('utf-8'))
        except Exception:
            raise StorageError('auth_cache_unavailable') from None

    def save(self, serialized_cache):
        if not serialized_cache.has_state_changed:
            return
        self._check_local()
        temporary, locked, success = None, False, False
        lock = self.path.with_name(self.path.name+'.lock')
        try:
            if self.path.is_symlink():raise StorageError('auth_cache_unavailable')
            self.path.parent.mkdir(parents=True,exist_ok=True)
            # No stale-lock deletion guess: a busy/crashed writer needs reviewed recovery.
            with lock.open('xb'):
                locked = True
            encrypted = self.protector.protect(serialized_cache.serialize().encode('utf-8'))
            temporary = self.path.with_name('.protected-cache-'+uuid4().hex+'.tmp')
            descriptor = os.open(temporary,os.O_CREAT | os.O_EXCL | os.O_WRONLY,0o600)
            with os.fdopen(descriptor,'wb') as stream:
                stream.write(encrypted);stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,self.path)
            success = True
        except FileExistsError:
            raise StorageError('auth_cache_busy') from None
        except StorageError:
            raise
        except Exception:
            raise StorageError('auth_cache_unavailable') from None
        finally:
            if not success:serialized_cache.has_state_changed = True
            try:
                if temporary is not None:temporary.unlink(missing_ok=True)
                if locked:lock.unlink(missing_ok=True)
            except OSError:
                raise StorageError('auth_cache_cleanup_required') from None
