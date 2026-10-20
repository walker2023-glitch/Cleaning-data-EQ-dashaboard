"""Disabled boundary: no SDK, credentials, token cache, or HTTP client in M0."""

from equipment_data_manager.storage.interface import RemoteFile


class IntegrationNotEnabledError(RuntimeError):
    """Microsoft integration is deferred to M2 after IT approval."""


class GraphSharePointRepository:
    """All operations fail before reading credentials or accessing the network."""

    def list_files(self, folder_id: str) -> tuple[RemoteFile, ...]:
        raise IntegrationNotEnabledError("SharePoint integration is disabled in M0.")

    def download(self, item_id: str, *, expected_etag: str) -> bytes:
        raise IntegrationNotEnabledError("SharePoint integration is disabled in M0.")

    def create_output(self, folder_id: str, *, name: str, content: bytes) -> RemoteFile:
        raise IntegrationNotEnabledError("SharePoint integration is disabled in M0.")
