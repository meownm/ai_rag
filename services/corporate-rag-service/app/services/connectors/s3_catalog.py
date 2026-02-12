from __future__ import annotations

import logging
import re
from datetime import datetime
from types import SimpleNamespace
from typing import Any

try:
    import boto3
except Exception:  # noqa: BLE001
    boto3 = None

from app.services.connectors.base import ConnectorError, ConnectorFetchResult, ConnectorListResult, SourceConnector, SourceDescriptor, SourceItem, SyncContext
from app.services.file_ingestion import FileByteIngestor

LOGGER = logging.getLogger(__name__)


def _load_settings() -> Any:
    try:
        from app.core.config import settings

        return settings
    except Exception:  # noqa: BLE001
        return SimpleNamespace(
            S3_ENDPOINT="http://localhost:9000",
            S3_ACCESS_KEY="minio",
            S3_SECRET_KEY="minio123",
            S3_REGION="us-east-1",
            S3_SECURE=False,
            S3_CATALOG_BUCKET="",
            S3_CATALOG_PREFIX="",
            S3_CATALOG_ALLOWED_EXTENSIONS=".pdf,.docx,.txt,.md",
            S3_CATALOG_MAX_OBJECT_MB=50,
        )


def _allowed_extensions(csv_value: str) -> set[str]:
    return {item.strip().lower() for item in csv_value.split(",") if item.strip()}


def _etag_safe(etag: str | None) -> str | None:
    if not etag:
        return None
    value = etag.strip('"')
    if re.fullmatch(r"[a-fA-F0-9]{32}", value):
        return value.lower()
    return None


class S3CatalogConnector(SourceConnector):
    source_type = "S3_CATALOG_OBJECT"

    def __init__(self, client: Any | None = None) -> None:
        self._ingestor = FileByteIngestor()
        self.client = client or self._build_client()

    def _build_client(self):
        cfg = _load_settings()
        if boto3 is None:
            raise RuntimeError("boto3 is required for S3 catalog connector")
        return boto3.client(
            "s3",
            endpoint_url=cfg.S3_ENDPOINT,
            aws_access_key_id=cfg.S3_ACCESS_KEY,
            aws_secret_access_key=cfg.S3_SECRET_KEY,
            region_name=cfg.S3_REGION,
            use_ssl=bool(cfg.S3_SECURE),
        )

    def is_configured(self) -> tuple[bool, str | None]:
        if not _load_settings().S3_CATALOG_BUCKET:
            return False, "S3_CATALOG_BUCKET is not configured"
        return True, None

    def list_descriptors(self, tenant_id: str, sync_context: SyncContext) -> ConnectorListResult:
        cfg = _load_settings()
        bucket = cfg.S3_CATALOG_BUCKET
        prefix = cfg.S3_CATALOG_PREFIX or ""
        allowed = _allowed_extensions(cfg.S3_CATALOG_ALLOWED_EXTENSIONS)
        max_bytes = int(cfg.S3_CATALOG_MAX_OBJECT_MB) * 1024 * 1024

        token: str | None = None
        descriptors: list[SourceDescriptor] = []
        seen: set[str] = set()
        exhausted_listing = False

        while True:
            params: dict[str, Any] = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": sync_context.page_size}
            if token:
                params["ContinuationToken"] = token
            response = self.client.list_objects_v2(**params)
            for obj in response.get("Contents", []) or []:
                key = str(obj.get("Key") or "")
                if not key or key in seen:
                    continue
                seen.add(key)
                suffix = "." + key.rsplit(".", 1)[-1].lower() if "." in key else ""
                if suffix not in allowed:
                    continue
                size_bytes = int(obj.get("Size") or 0)
                if size_bytes > max_bytes:
                    LOGGER.warning("s3_catalog_descriptor_skipped", extra={"event": "s3_catalog_descriptor_skipped", "error_code": "O-OBJECT-TOO-LARGE", "key": key})
                    continue
                last_modified = obj.get("LastModified")
                if isinstance(last_modified, str):
                    try:
                        last_modified = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
                    except ValueError:
                        last_modified = None
                checksum_hint = _etag_safe(obj.get("ETag"))
                descriptors.append(
                    SourceDescriptor(
                        source_type=self.source_type,
                        external_ref=f"s3:{bucket}:{key}",
                        title=key.rsplit("/", 1)[-1],
                        last_modified=last_modified,
                        checksum_hint=checksum_hint,
                        metadata={"bucket": bucket, "key": key, "etag": _etag_safe(obj.get("ETag")), "size_bytes": size_bytes, "last_modified": last_modified.isoformat() if last_modified else None},
                    )
                )
            if len(descriptors) >= sync_context.max_items_per_run:
                break
            if not response.get("IsTruncated"):
                exhausted_listing = True
                break
            token = response.get("NextContinuationToken")
            if not token:
                exhausted_listing = True
                break

        descriptors.sort(key=lambda d: str(d.metadata.get("key", "")))
        limited = descriptors[: sync_context.max_items_per_run]
        listing_complete = exhausted_listing
        return ConnectorListResult(descriptors=limited, listing_complete=listing_complete)

    def fetch_item(self, tenant_id: str, descriptor: SourceDescriptor) -> ConnectorFetchResult:
        cfg = _load_settings()
        key = str(descriptor.metadata.get("key") or "")
        bucket = str(descriptor.metadata.get("bucket") or cfg.S3_CATALOG_BUCKET)
        if not key:
            return ConnectorFetchResult(error=ConnectorError("O-KEY-MISSING", "Missing object key"))

        response = self.client.get_object(Bucket=bucket, Key=key)
        payload = response["Body"].read()
        max_bytes = int(cfg.S3_CATALOG_MAX_OBJECT_MB) * 1024 * 1024
        if len(payload) > max_bytes:
            return ConnectorFetchResult(error=ConnectorError("O-OBJECT-TOO-LARGE", f"Object exceeds size cap: {key}"))

        try:
            converted = self._ingestor.ingest_bytes(filename=descriptor.title, payload=payload)
        except ValueError as exc:
            return ConnectorFetchResult(error=ConnectorError("O-UNSUPPORTED-TYPE", str(exc)))
        markdown = (converted.markdown or "").strip()
        if not markdown:
            return ConnectorFetchResult(error=ConnectorError("O-EMPTY-MARKDOWN", f"Empty markdown from object: {key}"))

        return ConnectorFetchResult(
            item=SourceItem(
                source_type=self.source_type,
                external_ref=descriptor.external_ref,
                title=descriptor.title,
                markdown=markdown,
                metadata={**descriptor.metadata, "source": "s3"},
            )
        )
