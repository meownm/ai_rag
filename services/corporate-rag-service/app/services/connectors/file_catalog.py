from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.config import settings
from app.services.connectors.base import ConnectorError, ConnectorFetchResult, SourceConnector, SourceDescriptor, SourceItem, SyncContext
from app.services.file_ingestion import FileByteIngestor


class FileCatalogConnector(SourceConnector):
    source_type = "FILE_CATALOG_OBJECT"

    def __init__(self) -> None:
        self._ingestor = FileByteIngestor()

    def is_configured(self) -> tuple[bool, str | None]:
        if not settings.FILE_CATALOG_ROOT_PATH:
            return False, "FILE_CATALOG_ROOT_PATH is not configured"
        return True, None

    def list_descriptors(self, tenant_id: str, sync_context: SyncContext) -> list[SourceDescriptor]:
        root = Path(settings.FILE_CATALOG_ROOT_PATH)
        recursive = settings.FILE_CATALOG_RECURSIVE
        allowed = {item.strip().lower() for item in settings.FILE_CATALOG_ALLOWED_EXTENSIONS.split(",") if item.strip()}
        it = root.rglob("*") if recursive else root.glob("*")
        descriptors: list[SourceDescriptor] = []
        for path in sorted(p for p in it if p.is_file()):
            if path.suffix.lower() not in allowed:
                continue
            rel = path.relative_to(root).as_posix()
            stat = path.stat()
            checksum_hint = None
            if stat.st_size <= settings.FILE_CATALOG_MAX_FILE_MB * 1024 * 1024:
                checksum_hint = hashlib.sha256(path.read_bytes()).hexdigest()
            descriptors.append(
                SourceDescriptor(
                    source_type=self.source_type,
                    external_ref=f"fs:{rel}",
                    title=path.name,
                    last_modified=None,
                    checksum_hint=checksum_hint,
                    metadata={"rel_path": rel, "full_path": str(path), "size_bytes": stat.st_size},
                )
            )
            if len(descriptors) >= sync_context.max_items_per_run:
                break
        return descriptors

    def fetch_item(self, tenant_id: str, descriptor: SourceDescriptor) -> ConnectorFetchResult:
        full_path = Path(str(descriptor.metadata.get("full_path", "")))
        if not full_path.exists():
            return ConnectorFetchResult(error=ConnectorError("F-FILE-NOT-FOUND", f"File not found: {full_path}"))
        payload = full_path.read_bytes()
        max_bytes = settings.FILE_CATALOG_MAX_FILE_MB * 1024 * 1024
        if len(payload) > max_bytes:
            return ConnectorFetchResult(error=ConnectorError("F-FILE-TOO-LARGE", f"File exceeds size cap: {full_path}"))
        try:
            converted = self._ingestor.ingest_bytes(filename=full_path.name, payload=payload)
        except ValueError as exc:
            return ConnectorFetchResult(error=ConnectorError("F-UNSUPPORTED-TYPE", str(exc)))
        return ConnectorFetchResult(
            item=SourceItem(
                source_type=self.source_type,
                external_ref=descriptor.external_ref,
                title=descriptor.title,
                markdown=converted.markdown,
                metadata=descriptor.metadata,
            )
        )
