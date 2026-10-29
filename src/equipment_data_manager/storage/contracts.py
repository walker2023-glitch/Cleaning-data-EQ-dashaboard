"""Provider-neutral read contracts; no identity is a basename alone."""
from dataclasses import dataclass, field
from typing import Protocol
from equipment_data_manager.processing.models import ProcessingError


class StorageError(ProcessingError):
    """Category-only errors, compatible with the existing processing/UI boundary."""


@dataclass(frozen=True, repr=False)
class StorageFile:
    provider: str
    container: str
    parent_id: str
    item_id: str
    name: str
    size_bytes: int
    version: str
    sha256: str | None = None


@dataclass(frozen=True, repr=False)
class FileRead:
    content: bytes = field(repr=False)
    sha256: str
    version: str
    integrity: str
    sync_verified: bool = False


class StorageProvider(Protocol):
    def list_files(self, folder_id: str) -> tuple[StorageFile, ...]: ...
    def read(self, source: StorageFile, *, expected_sha256: str | None = None) -> FileRead: ...
