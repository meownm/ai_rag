import uuid

from tests.unit.test_ingestion_pipeline import FakeDb, FakeStorage

from app.services.ingestion import ingest_sources_sync


class FakeConfluenceAttachmentConnector:
    source_type = "CONFLUENCE_ATTACHMENT"

    def is_configured(self):
        return True, None

    def list_descriptors(self, tenant_id, sync_context):
        from app.services.connectors.base import SourceDescriptor

        return [
            SourceDescriptor(
                source_type=self.source_type,
                external_ref="attachment:att-1",
                title="handbook.md",
                checksum_hint="v:1",
                metadata={"container_id": "page-1"},
            )
        ]

    def fetch_item(self, tenant_id, descriptor):
        from app.services.connectors.base import ConnectorFetchResult, SourceItem

        return ConnectorFetchResult(
            item=SourceItem(
                source_type=self.source_type,
                external_ref=descriptor.external_ref,
                title=descriptor.title,
                markdown="# Handbook\n\nWelcome",
                metadata={"containerId": "page-1", "containerType": "page"},
            )
        )


class FakeRegistry:
    def __init__(self):
        self.connector = FakeConfluenceAttachmentConnector()

    def get(self, source_type):
        return self.connector


def test_confluence_attachment_ingestion_flow_integration(monkeypatch):
    db = FakeDb()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")

    class FakeEmbeddingsClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def embed_texts(self, texts, **_kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

    monkeypatch.setattr("app.services.ingestion.EmbeddingsClient", FakeEmbeddingsClient)
    monkeypatch.setattr("app.services.ingestion.register_default_connectors", lambda: FakeRegistry())

    result = ingest_sources_sync(db, tenant, ["CONFLUENCE_ATTACHMENT"], storage=FakeStorage())

    assert result["documents"] == 1
    assert any("INSERT INTO source_sync_state" in stmt for stmt, _ in db.calls)
