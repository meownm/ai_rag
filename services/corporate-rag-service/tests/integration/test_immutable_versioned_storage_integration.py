import uuid

from app.services.connectors.base import ConnectorFetchResult, ConnectorListResult, SourceDescriptor, SourceItem
from app.services.ingestion import ingest_sources_sync
from tests.unit.test_ingestion_pipeline import FakeDb, FakeStorage


class _MutableBinaryConnector:
    source_type = "FILE_CATALOG_OBJECT"

    def __init__(self):
        self.rev = 1

    def is_configured(self):
        return True, None

    def list_descriptors(self, tenant_id, sync_context):
        return ConnectorListResult(
            descriptors=[
                SourceDescriptor(
                    source_type=self.source_type,
                    external_ref="fs:versioned.bin",
                    title="versioned.bin",
                    checksum_hint=f"rev:{self.rev}",
                )
            ],
            listing_complete=True,
        )

    def fetch_item(self, tenant_id, descriptor):
        payload = f"binary-rev-{self.rev}".encode("utf-8")
        return ConnectorFetchResult(
            item=SourceItem(
                source_type=self.source_type,
                external_ref=descriptor.external_ref,
                title=descriptor.title,
                markdown=f"# rev {self.rev}",
            ),
            raw_payload=payload,
        )


class _Registry:
    def __init__(self, connector):
        self.connector = connector

    def get(self, source_type):
        return self.connector


def test_immutable_versioned_storage_creates_distinct_source_versions_for_modified_content(monkeypatch):
    db = FakeDb()
    storage = FakeStorage()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    connector = _MutableBinaryConnector()

    class FakeEmbeddingsClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def embed_texts(self, texts, **_kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

    monkeypatch.setattr("app.services.ingestion.EmbeddingsClient", FakeEmbeddingsClient)

    ingest_sources_sync(db, tenant, ["FILE_CATALOG_OBJECT"], storage=storage, connector_registry=_Registry(connector))
    connector.rev = 2
    ingest_sources_sync(db, tenant, ["FILE_CATALOG_OBJECT"], storage=storage, connector_registry=_Registry(connector))

    assert len(db.source_versions) == 2
    raw_keys = [key for bucket, key, _ in storage.put_calls if bucket == "rag-raw" and key.endswith("/raw.bin")]
    assert len(raw_keys) == 2
    assert raw_keys[0] != raw_keys[1]


def test_immutable_versioned_storage_skips_duplicate_version_for_identical_content(monkeypatch):
    db = FakeDb()
    storage = FakeStorage()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    connector = _MutableBinaryConnector()

    class FakeEmbeddingsClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def embed_texts(self, texts, **_kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

    monkeypatch.setattr("app.services.ingestion.EmbeddingsClient", FakeEmbeddingsClient)

    ingest_sources_sync(db, tenant, ["FILE_CATALOG_OBJECT"], storage=storage, connector_registry=_Registry(connector))
    ingest_sources_sync(db, tenant, ["FILE_CATALOG_OBJECT"], storage=storage, connector_registry=_Registry(connector))

    assert len(db.source_versions) == 1
    raw_keys = [key for bucket, key, _ in storage.put_calls if bucket == "rag-raw" and key.endswith("/raw.bin")]
    assert len(raw_keys) == 1
