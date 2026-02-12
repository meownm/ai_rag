from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class SourceSyncState:
    tenant_id: str
    source_type: str
    external_ref: str
    last_seen_modified_at: datetime | None
    last_seen_checksum: str | None
    last_synced_at: datetime | None
    last_status: str
    last_error_code: str | None
    last_error_message: str | None


class SourceSyncStateRepository:
    def __init__(self, db: Any):
        self.db = db

    def get_state(self, tenant_id: str, source_type: str, external_ref: str) -> SourceSyncState | None:
        result = self.db.execute(
            """
            SELECT tenant_id, source_type, external_ref, last_seen_modified_at, last_seen_checksum,
                   last_synced_at, last_status, last_error_code, last_error_message
            FROM source_sync_state
            WHERE tenant_id = :tenant_id AND source_type = :source_type AND external_ref = :external_ref
            """,
            {"tenant_id": tenant_id, "source_type": source_type, "external_ref": external_ref},
        )
        if not hasattr(result, "mappings"):
            return None
        row = result.mappings().first()
        if not row:
            return None
        return SourceSyncState(**row)

    def upsert_state(
        self,
        *,
        tenant_id: str,
        source_type: str,
        external_ref: str,
        last_seen_modified_at: datetime | None,
        last_seen_checksum: str | None,
        last_synced_at: datetime | None,
        last_status: str,
        last_error_code: str | None,
        last_error_message: str | None,
    ) -> None:
        self.db.execute(
            """
            INSERT INTO source_sync_state (
                tenant_id, source_type, external_ref, last_seen_modified_at, last_seen_checksum,
                last_synced_at, last_status, last_error_code, last_error_message
            ) VALUES (
                :tenant_id, :source_type, :external_ref, :last_seen_modified_at, :last_seen_checksum,
                :last_synced_at, :last_status, :last_error_code, :last_error_message
            )
            ON CONFLICT (tenant_id, source_type, external_ref)
            DO UPDATE SET
                last_seen_modified_at = EXCLUDED.last_seen_modified_at,
                last_seen_checksum = EXCLUDED.last_seen_checksum,
                last_synced_at = EXCLUDED.last_synced_at,
                last_status = EXCLUDED.last_status,
                last_error_code = EXCLUDED.last_error_code,
                last_error_message = EXCLUDED.last_error_message
            """,
            {
                "tenant_id": tenant_id,
                "source_type": source_type,
                "external_ref": external_ref,
                "last_seen_modified_at": last_seen_modified_at,
                "last_seen_checksum": last_seen_checksum,
                "last_synced_at": last_synced_at,
                "last_status": last_status,
                "last_error_code": last_error_code,
                "last_error_message": (last_error_message or "")[:512] or None,
            },
        )

    def mark_success(
        self,
        *,
        tenant_id: str,
        source_type: str,
        external_ref: str,
        last_seen_modified_at: datetime | None,
        last_seen_checksum: str | None,
        last_synced_at: datetime,
    ) -> None:
        self.upsert_state(
            tenant_id=tenant_id,
            source_type=source_type,
            external_ref=external_ref,
            last_seen_modified_at=last_seen_modified_at,
            last_seen_checksum=last_seen_checksum,
            last_synced_at=last_synced_at,
            last_status="success",
            last_error_code=None,
            last_error_message=None,
        )

    def mark_failure(
        self,
        *,
        tenant_id: str,
        source_type: str,
        external_ref: str,
        last_seen_modified_at: datetime | None,
        last_seen_checksum: str | None,
        last_synced_at: datetime,
        error_code: str,
        error_message: str,
    ) -> None:
        self.upsert_state(
            tenant_id=tenant_id,
            source_type=source_type,
            external_ref=external_ref,
            last_seen_modified_at=last_seen_modified_at,
            last_seen_checksum=last_seen_checksum,
            last_synced_at=last_synced_at,
            last_status="failed",
            last_error_code=error_code,
            last_error_message=error_message,
        )
