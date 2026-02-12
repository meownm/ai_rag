from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.services.connectors.base import ConnectorError, ConnectorFetchResult, SourceConnector, SourceDescriptor, SourceItem, SyncContext
from app.services.file_ingestion import FileByteIngestor

LOGGER = logging.getLogger(__name__)


def _load_settings() -> Any:
    try:
        from app.core.config import settings

        return settings
    except Exception:  # noqa: BLE001
        return SimpleNamespace(
            FILE_CATALOG_ROOT_PATH="",
            FILE_CATALOG_RECURSIVE=True,
            FILE_CATALOG_ALLOWED_EXTENSIONS=".pdf,.docx,.txt,.md",
            FILE_CATALOG_MAX_FILE_MB=50,
        )


def _allowed_extensions(csv_value: str) -> set[str]:
    return {item.strip().lower() for item in csv_value.split(",") if item.strip()}


def _normalize_rel_path(path: Path) -> str:
    return path.as_posix().replace("\\", "/")


class FileCatalogConnector(SourceConnector):
    source_type = "FILE_CATALOG_OBJECT"

    def __init__(self) -> None:
        self._ingestor = FileByteIngestor()

    def is_configured(self) -> tuple[bool, str | None]:
        cfg = _load_settings()
        if not cfg.FILE_CATALOG_ROOT_PATH:
            return False, "FILE_CATALOG_ROOT_PATH is not configured"
        return True, None

    def _iter_files(self, root: Path, recursive: bool):
        if recursive:
            for dirpath, _dirnames, filenames in __import__("os").walk(root):
                for filename in filenames:
                    yield Path(dirpath) / filename
        else:
            for entry in root.iterdir():
                if entry.is_file():
                    yield entry

    def list_descriptors(self, tenant_id: str, sync_context: SyncContext) -> list[SourceDescriptor]:
        cfg = _load_settings()
        root = Path(cfg.FILE_CATALOG_ROOT_PATH).resolve()
        recursive = bool(cfg.FILE_CATALOG_RECURSIVE)
        allowed = _allowed_extensions(cfg.FILE_CATALOG_ALLOWED_EXTENSIONS)
        max_bytes = int(cfg.FILE_CATALOG_MAX_FILE_MB) * 1024 * 1024

        descriptors: list[SourceDescriptor] = []
        files_scanned = 0
        files_skipped = 0
        total_bytes = 0
        started = datetime.now(timezone.utc)
        for path in self._iter_files(root, recursive):
            files_scanned += 1
            try:
                resolved = path.resolve()
            except OSError:
                LOGGER.warning("file_catalog_descriptor_skipped", extra={"event": "file_catalog_descriptor_skipped", "error_code": "F-SEC-RESOLVE-FAILED", "path": str(path)})
                files_skipped += 1
                continue

            # boundary + symlink escape protection
            if root not in resolved.parents and resolved != root:
                LOGGER.warning(
                    "file_catalog_descriptor_skipped",
                    extra={"event": "file_catalog_descriptor_skipped", "error_code": "F-SEC-SYMLINK-ESCAPE", "path": str(path), "resolved": str(resolved)},
                )
                files_skipped += 1
                continue

            suffix = resolved.suffix.lower()
            if suffix not in allowed:
                files_skipped += 1
                continue

            rel = _normalize_rel_path(resolved.relative_to(root))
            if ".." in rel.split("/"):
                LOGGER.warning(
                    "file_catalog_descriptor_skipped",
                    extra={"event": "file_catalog_descriptor_skipped", "error_code": "F-SEC-PATH-TRAVERSAL", "rel_path": rel},
                )
                files_skipped += 1
                continue

            stat = resolved.stat()
            if stat.st_size > max_bytes:
                LOGGER.warning(
                    "file_catalog_descriptor_skipped",
                    extra={"event": "file_catalog_descriptor_skipped", "error_code": "F-FILE-TOO-LARGE", "rel_path": rel, "size_bytes": stat.st_size},
                )
                files_skipped += 1
                continue

            checksum_hint = hashlib.sha256(resolved.read_bytes()).hexdigest()
            total_bytes += stat.st_size
            descriptors.append(
                SourceDescriptor(
                    source_type=self.source_type,
                    external_ref=f"fs:{rel}",
                    title=resolved.name,
                    last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    checksum_hint=checksum_hint,
                    metadata={
                        "size_bytes": stat.st_size,
                        "rel_path": rel,
                        "abs_path": str(resolved),
                        "last_modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    },
                )
            )

        descriptors.sort(key=lambda d: d.external_ref)
        if len(descriptors) > sync_context.max_items_per_run:
            LOGGER.warning(
                "file_catalog_cap_exceeded",
                extra={"event": "file_catalog_cap_exceeded", "files_scanned": len(descriptors), "max_items": sync_context.max_items_per_run},
            )
        final = descriptors[: sync_context.max_items_per_run]
        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        LOGGER.info(
            "file_catalog_summary",
            extra={
                "event": "file_catalog_summary",
                "files_scanned": files_scanned,
                "files_skipped": files_skipped,
                "files_ingested": len(final),
                "total_bytes": total_bytes,
                "total_duration": duration_ms,
            },
        )
        return final

    def fetch_item(self, tenant_id: str, descriptor: SourceDescriptor) -> ConnectorFetchResult:
        full_path = Path(str(descriptor.metadata.get("abs_path", "")))
        cfg = _load_settings()
        root = Path(cfg.FILE_CATALOG_ROOT_PATH).resolve()
        try:
            resolved = full_path.resolve()
        except OSError:
            return ConnectorFetchResult(error=ConnectorError("F-SEC-RESOLVE-FAILED", f"Cannot resolve path: {full_path}"))
        if root not in resolved.parents and resolved != root:
            return ConnectorFetchResult(error=ConnectorError("F-SEC-SYMLINK-ESCAPE", f"Path escapes root: {resolved}"))
        if not resolved.exists():
            return ConnectorFetchResult(error=ConnectorError("F-FILE-NOT-FOUND", f"File not found: {resolved}"))

        payload = resolved.read_bytes()
        max_bytes = int(cfg.FILE_CATALOG_MAX_FILE_MB) * 1024 * 1024
        if len(payload) > max_bytes:
            return ConnectorFetchResult(error=ConnectorError("F-FILE-TOO-LARGE", f"File exceeds size cap: {resolved}"))

        try:
            converted = self._ingestor.ingest_bytes(filename=resolved.name, payload=payload)
        except ValueError as exc:
            return ConnectorFetchResult(error=ConnectorError("F-UNSUPPORTED-TYPE", str(exc)))

        markdown = (converted.markdown or "").strip()
        if not markdown:
            return ConnectorFetchResult(error=ConnectorError("F-EMPTY-MARKDOWN", f"Empty markdown from file: {resolved}"))

        return ConnectorFetchResult(
            item=SourceItem(
                source_type=self.source_type,
                external_ref=descriptor.external_ref,
                title=descriptor.title,
                markdown=markdown,
                metadata={**descriptor.metadata, "source": "fs"},
            )
        )
