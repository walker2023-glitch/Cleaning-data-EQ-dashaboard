"""Proposed storage boundary; identifiers are opaque, not filesystem paths."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RemoteFile:
    item_id: str
    name: str
    size_bytes: int
    etag: str


class ReportRepository(Protocol):
    def list_files(self, folder_id: str) -> tuple[RemoteFile, ...]:
        """List all pages within an approved folder, or raise on failure."""
        ...

    def download(self, item_id: str, *, expected_etag: str) -> bytes:
        """Read the expected version; fail on conflict or access denial."""
        ...

    def create_output(self, folder_id: str, *, name: str, content: bytes) -> RemoteFile:
        """Create validated output only if absent; never overwrite.

        A future coordinator must validate and obtain confirmation first.
        Replacements/staging need a separate reviewed contract in M1/M2.
        """
        ...
