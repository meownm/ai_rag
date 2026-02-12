from __future__ import annotations

from app.core.config import settings
from app.services.connectors.base import ConnectorError, ConnectorFetchResult, SourceConnector, SourceDescriptor, SyncContext


class ConfluenceConnector(SourceConnector):
    source_type = "CONFLUENCE_PAGE"

    def is_configured(self) -> tuple[bool, str | None]:
        if not settings.CONFLUENCE_BASE_URL:
            return False, "CONFLUENCE_BASE_URL is not configured"
        if settings.CONFLUENCE_AUTH_MODE == "pat" and not settings.CONFLUENCE_PAT:
            return False, "CONFLUENCE_PAT is required for pat auth"
        return True, None

    def list_descriptors(self, tenant_id: str, sync_context: SyncContext) -> list[SourceDescriptor]:
        return []

    def fetch_item(self, tenant_id: str, descriptor: SourceDescriptor) -> ConnectorFetchResult:
        return ConnectorFetchResult(error=ConnectorError("C-NOT-IMPLEMENTED", "Confluence connector implementation pending"))


class ConfluenceAttachmentConnector(ConfluenceConnector):
    source_type = "CONFLUENCE_ATTACHMENT"


class S3CatalogConnector(SourceConnector):
    source_type = "S3_CATALOG_OBJECT"

    def is_configured(self) -> tuple[bool, str | None]:
        if not settings.S3_CATALOG_BUCKET:
            return False, "S3_CATALOG_BUCKET is not configured"
        return True, None

    def list_descriptors(self, tenant_id: str, sync_context: SyncContext) -> list[SourceDescriptor]:
        return []

    def fetch_item(self, tenant_id: str, descriptor: SourceDescriptor) -> ConnectorFetchResult:
        return ConnectorFetchResult(error=ConnectorError("O-NOT-IMPLEMENTED", "S3 catalog connector implementation pending"))
