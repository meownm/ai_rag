import uuid

from app.services.ingestion import SourceItem, chunk_markdown, ingest_sources_sync, stable_chunk_id


class FakeMappings:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeResult:
    rowcount = 1

    def __init__(self, rows=None):
        self._rows = rows or []

    def mappings(self):
        return FakeMappings(self._rows)


class FakeDb:
    def __init__(self):
        self.calls = []

    def execute(self, statement, params=None):
        stmt = str(statement)
        payload = params or {}
        self.calls.append((stmt, payload))
        if "SELECT chunk_id, chunk_text FROM chunks" in stmt:
            chunk_ids = payload.get("chunk_ids", [])
            return FakeResult([{"chunk_id": cid, "chunk_text": "chunk text"} for cid in chunk_ids])
        return FakeResult()

    def commit(self):
        return None


class FakeStorage:
    def __init__(self):
        self.put_calls = []

    def put_text(self, bucket: str, key: str, text: str) -> str:
        self.put_calls.append((bucket, key, text))
        return f"s3://{bucket}/{key}"


class FakeConfluence:
    def crawl(self, tenant_id):
        return [
            SourceItem(
                source_type="CONFLUENCE_PAGE",
                external_ref="page:1",
                title="Policy",
                markdown="# Policy\nVacation policy text with [link](https://conf.local/page/2)",
                url="https://conf.local/page/1",
                author="admin",
                labels=["hr"],
            )
        ]


class FakeCatalog:
    def crawl(self, tenant_id):
        return [
            SourceItem(
                source_type="FILE_CATALOG_OBJECT",
                external_ref="file:a.md",
                title="Catalog",
                markdown="# Catalog\nAttachment content",
            )
        ]


def test_stable_chunk_id_is_deterministic_positive():
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    doc = uuid.UUID("22222222-2222-2222-2222-222222222222")
    ver = uuid.UUID("33333333-3333-3333-3333-333333333333")
    c1 = stable_chunk_id(tenant, doc, ver, 0, "same text")
    c2 = stable_chunk_id(tenant, doc, ver, 0, "same   text")
    assert c1 == c2


def test_chunk_markdown_negative_empty():
    assert chunk_markdown("   \n\n") == []


def test_ingest_sources_sync_inserts_docs_chunks_links_and_s3_positive(monkeypatch):
    db = FakeDb()
    storage = FakeStorage()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    class FakeEmbeddingsClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def embed_text(self, *_args, **_kwargs):
            return [0.1, 0.2, 0.3]

    monkeypatch.setattr("app.services.ingestion.EmbeddingsClient", FakeEmbeddingsClient)

    result = ingest_sources_sync(
        db,
        tenant,
        ["CONFLUENCE_PAGE", "FILE_CATALOG_OBJECT"],
        confluence=FakeConfluence(),
        file_catalog=FakeCatalog(),
        storage=storage,
    )
    assert result["documents"] == 2
    assert result["chunks"] >= 2
    assert result["cross_links"] >= 1
    assert result["artifacts"] == 2

    sql_text = "\n".join(call[0] for call in db.calls)
    assert "INSERT INTO documents" in sql_text
    assert "INSERT INTO chunks" in sql_text
    assert "INSERT INTO cross_links" in sql_text
    assert "INSERT INTO source_versions" in sql_text
    assert "INSERT INTO chunk_vectors" in sql_text
    assert "INSERT INTO chunk_fts" in sql_text

    buckets = [x[0] for x in storage.put_calls]
    assert "rag-raw" in buckets
    assert "rag-markdown" in buckets


def test_ingest_sources_sync_negative_unknown_source_type_no_data():
    db = FakeDb()
    storage = FakeStorage()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    result = ingest_sources_sync(db, tenant, ["UNKNOWN"], storage=storage)
    assert result == {"documents": 0, "chunks": 0, "cross_links": 0, "artifacts": 0}
    assert db.calls == []
    assert storage.put_calls == []
