import uuid
from datetime import datetime, timezone

from app.services.connectors.base import ConnectorFetchResult, ConnectorListResult, SourceDescriptor, SourceItem
from app.services.ingestion import ingest_sources_sync
from tests.unit.test_ingestion_pipeline import FakeDb, FakeStorage


class _BaseConnector:
    source_type = "FILE_CATALOG_OBJECT"

    def is_configured(self):
        return True, None

    def fetch_item(self, tenant_id, descriptor):
        return ConnectorFetchResult(
            item=SourceItem(
                source_type=self.source_type,
                external_ref=descriptor.external_ref,
                title=descriptor.title,
                markdown="# Current",
            )
        )


class _TruncatedListingConnector(_BaseConnector):
    def list_descriptors(self, tenant_id, sync_context):
        return ConnectorListResult(
            descriptors=[SourceDescriptor(source_type=self.source_type, external_ref="fs:a.md", title="A")],
            listing_complete=False,
        )


class _AuthoritativeListingConnector(_BaseConnector):
    def list_descriptors(self, tenant_id, sync_context):
        return ConnectorListResult(
            descriptors=[SourceDescriptor(source_type=self.source_type, external_ref="fs:a.md", title="A")],
            listing_complete=True,
        )


class _Registry:
    def __init__(self, connector):
        self.connector = connector

    def get(self, source_type):
        return self.connector


def _seed_sync_state(db: FakeDb, tenant_id: uuid.UUID) -> None:
    now = datetime.now(timezone.utc)
    tenant = str(tenant_id)
    db.sync_state[(tenant, "FILE_CATALOG_OBJECT", "fs:a.md")] = {
        "tenant_id": tenant,
        "source_type": "FILE_CATALOG_OBJECT",
        "external_ref": "fs:a.md",
        "last_seen_modified_at": now,
        "last_seen_checksum": "h1",
        "last_synced_at": now,
        "last_status": "success",
        "last_error_code": None,
        "last_error_message": None,
    }
    db.sync_state[(tenant, "FILE_CATALOG_OBJECT", "fs:legacy.md")] = {
        "tenant_id": tenant,
        "source_type": "FILE_CATALOG_OBJECT",
        "external_ref": "fs:legacy.md",
        "last_seen_modified_at": now,
        "last_seen_checksum": "h2",
        "last_synced_at": now,
        "last_status": "success",
        "last_error_code": None,
        "last_error_message": None,
    }


def test_tombstone_safety_skips_deletion_for_non_authoritative_listing(monkeypatch):
    db = FakeDb()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    _seed_sync_state(db, tenant)

    class FakeEmbeddingsClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def embed_texts(self, texts, **_kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

    monkeypatch.setattr("app.services.ingestion.EmbeddingsClient", FakeEmbeddingsClient)

    ingest_sources_sync(
        db,
        tenant,
        ["FILE_CATALOG_OBJECT"],
        storage=FakeStorage(),
        connector_registry=_Registry(_TruncatedListingConnector()),
    )

    legacy_row = db.sync_state[(str(tenant), "FILE_CATALOG_OBJECT", "fs:legacy.md")]
    assert legacy_row["last_status"] != "deleted"
    assert all("DELETE FROM source_versions" not in stmt for stmt, _ in db.calls)


def test_tombstone_authoritative_listing_marks_missing_source_deleted(monkeypatch):
    db = FakeDb()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    _seed_sync_state(db, tenant)

    class FakeEmbeddingsClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def embed_texts(self, texts, **_kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

    monkeypatch.setattr("app.services.ingestion.EmbeddingsClient", FakeEmbeddingsClient)

    ingest_sources_sync(
        db,
        tenant,
        ["FILE_CATALOG_OBJECT"],
        storage=FakeStorage(),
        connector_registry=_Registry(_AuthoritativeListingConnector()),
    )

    legacy_row = db.sync_state[(str(tenant), "FILE_CATALOG_OBJECT", "fs:legacy.md")]
    assert legacy_row["last_status"] == "deleted"
