"""Read-only local/synced files: existence is not proof of availability or sync."""
from hashlib import sha256
from pathlib import Path
import stat

from equipment_data_manager.storage.contracts import FileRead, StorageError, StorageFile

# Windows offline / recall-on-open / recall-on-data-access. Never auto-hydrate.
UNAVAILABLE_ATTRIBUTES = 0x1000 | 0x40000 | 0x400000


def _stat(path):
    try:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise StorageError('input_not_a_file')
        if getattr(info, 'st_file_attributes', 0) & UNAVAILABLE_ATTRIBUTES:
            raise StorageError('storage_file_not_downloaded')
        return info
    except FileNotFoundError:
        raise StorageError('input_not_a_file') from None
    except PermissionError:
        raise StorageError('storage_access_denied') from None
    except OSError:
        raise StorageError('storage_file_unavailable') from None


def _version(info):
    return f'{info.st_dev}:{info.st_ino}:{info.st_size}:{info.st_mtime_ns}:{info.st_ctime_ns}'


def read_local_file(path: Path, *, expected_version=None, expected_sha256=None):
    """Read stable bounded-by-original-size bytes; original is never written.

    A before/after identity/length check detects changes and interrupted reads,
    not remote sync completion. Arbitrary mid-write applications still need an
    export-complete/operator handoff; no local check proves server currency.
    """
    path = Path(path)
    before = _stat(path)
    version = _version(before)
    if expected_version is not None and expected_version != version:
        raise StorageError('storage_source_changed')
    try:
        with path.open('rb') as stream:
            raw = stream.read(before.st_size + 1)
    except PermissionError:
        raise StorageError('storage_access_denied') from None
    except OSError:
        raise StorageError('storage_file_unavailable') from None
    after = _stat(path)
    if version != _version(after) or len(raw) != before.st_size:
        raise StorageError('storage_source_changed_or_partial')
    digest = sha256(raw).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise StorageError('storage_source_hash_mismatch')
    return FileRead(raw, digest, version, 'local_bytes_read_stably_sync_unverified')


class LocalFolderStorage:
    """The same read contract for local or synced raw roots; no write API."""
    def __init__(self, root: Path, *, synced=False):
        self.root = Path(root).resolve()
        self.provider = 'synced-local' if synced else 'local'

    def _path(self, relative):
        if not relative or Path(relative).is_absolute() or '..' in Path(relative).parts:
            raise StorageError('storage_path_rejected')
        path = self.root / relative
        if not path.resolve().is_relative_to(self.root) or any(
                p.is_symlink() or p.is_junction() for p in (path, *path.parents) if p != self.root):
            raise StorageError('storage_path_rejected')
        return path

    def list_files(self, folder_id):
        folder = self._path(folder_id)
        try:
            entries = sorted(folder.iterdir())
        except FileNotFoundError:
            raise StorageError('storage_folder_missing') from None
        except PermissionError:
            raise StorageError('storage_access_denied') from None
        except OSError:
            raise StorageError('storage_folder_unavailable') from None
        result = []
        for path in entries:
            if path.name.startswith(('.', '~')) or path.is_symlink() or path.is_junction() or not path.is_file():
                continue
            # Listing records identity, not availability; placeholders fail on read.
            try:
                info = path.stat()
            except OSError:
                raise StorageError('storage_folder_changed_or_unavailable') from None
            result.append(StorageFile(self.provider, str(self.root), str(Path(folder_id)),
                str(path.relative_to(self.root)), path.name, info.st_size, _version(info)))
        return tuple(result)

    def read(self, source, *, expected_sha256=None):
        if source.provider != self.provider or source.container != str(self.root):
            raise StorageError('storage_reference_rejected')
        path = self._path(source.item_id)
        if str(path.parent.relative_to(self.root)) != source.parent_id or path.name != source.name:
            raise StorageError('storage_reference_rejected')
        return read_local_file(path, expected_version=source.version,
                               expected_sha256=expected_sha256 or source.sha256)
