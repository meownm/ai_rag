"""Connector for in-memory file uploads received via the REST API."""

from __future__ import annotations

from app.services.connectors.base import ConnectorFetchResult, SourceDescriptor, SyncContext
from app.services.file_ingestion import FileByteIngestor


class UploadConnector:
    """Wraps a single uploaded file as a connector so it can be processed
    through the standard ingestion pipeline."""

    source_type = "FILE_UPLOAD_OBJECT"

    def __init__(self, upload_name: str, upload_payload: bytes) -> None:
        self._filename = upload_name or "upload.bin"
        self._payload = upload_payload
        self._item = FileByteIngestor().ingest_bytes(filename=self._filename, payload=upload_payload)

    def is_configured(self) -> tuple[bool, str | None]:
        return True, None

    def list_descriptors(self, tenant: str, sync_context: SyncContext) -> list[SourceDescriptor]:
        return [SourceDescriptor(source_type=self.source_type, external_ref=self._item.external_ref, title=self._item.title)]

    def fetch_item(self, tenant: str, descriptor: SourceDescriptor) -> ConnectorFetchResult:
        return ConnectorFetchResult(item=self._item, raw_payload=self._payload)
