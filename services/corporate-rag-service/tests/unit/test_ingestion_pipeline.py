import uuid

import pytest

from app.services.ingestion import EmbeddingIndexingError, SourceItem, _upsert_chunk_vectors, chunk_markdown, ingest_sources_sync, stable_chunk_id


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
        if "SELECT c.chunk_id, c.chunk_text" in stmt and "LEFT JOIN chunk_vectors" in stmt:
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

        def embed_texts(self, texts, **_kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

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


def test_upsert_chunk_vectors_retries_then_succeeds(monkeypatch):
    db = FakeDb()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    calls = {"n": 0}

    class RetryEmbeddingsClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def embed_texts(self, texts, **_kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("temporary")
            return [[0.1, 0.2, 0.3] for _ in texts]

    class FakeSettings:
        EMBEDDINGS_BATCH_SIZE = 2
        EMBEDDINGS_RETRY_ATTEMPTS = 3
        EMBEDDINGS_DEFAULT_MODEL_ID = "bge-m3"
        EMBEDDINGS_SERVICE_URL = "http://localhost:8200"
        EMBEDDINGS_TIMEOUT_SECONDS = 30

    monkeypatch.setattr("app.services.ingestion.EmbeddingsClient", RetryEmbeddingsClient)
    monkeypatch.setattr("app.services.ingestion._load_settings", lambda: FakeSettings())
    monkeypatch.setattr("app.services.ingestion.time.sleep", lambda *_args, **_kwargs: None)

    chunk_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    _upsert_chunk_vectors(db, tenant, chunk_ids)

    assert calls["n"] == 3
    sql_text = "\n".join(call[0] for call in db.calls)
    assert "LEFT JOIN chunk_vectors" in sql_text
    assert "ON CONFLICT (chunk_id) DO UPDATE" in sql_text


def test_upsert_chunk_vectors_raises_after_retries_exhausted(monkeypatch):
    db = FakeDb()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")

    class AlwaysFailEmbeddingsClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def embed_texts(self, texts, **_kwargs):
            raise RuntimeError("down")

    class FakeSettings:
        EMBEDDINGS_BATCH_SIZE = 2
        EMBEDDINGS_RETRY_ATTEMPTS = 2
        EMBEDDINGS_DEFAULT_MODEL_ID = "bge-m3"
        EMBEDDINGS_SERVICE_URL = "http://localhost:8200"
        EMBEDDINGS_TIMEOUT_SECONDS = 30

    monkeypatch.setattr("app.services.ingestion.EmbeddingsClient", AlwaysFailEmbeddingsClient)
    monkeypatch.setattr("app.services.ingestion._load_settings", lambda: FakeSettings())
    monkeypatch.setattr("app.services.ingestion.time.sleep", lambda *_args, **_kwargs: None)

    with pytest.raises(EmbeddingIndexingError):
        _upsert_chunk_vectors(db, tenant, [uuid.uuid4()])


def test_chunk_markdown_respects_min_max_and_overlap_positive():
    text = "# H1\n" + ("alpha " * 1000)
    chunks = chunk_markdown(text, target_tokens=650, max_tokens=900, min_tokens=120, overlap_tokens=80)

    assert len(chunks) >= 2
    assert all(c["token_count"] <= 900 for c in chunks)
    # overlap for paragraph/mixed keeps repeated boundary tokens
    first_tail = chunks[0]["chunk_text"].split()[-5:]
    second_head = chunks[1]["chunk_text"].split()[:5]
    assert first_tail == second_head


def test_chunk_markdown_contract_boundaries_positive():
    markdown = """# Policy

Paragraph one sentence.

- item one
- item two

> quoted text

```
code line
```
"""
    chunks = chunk_markdown(markdown, target_tokens=20, max_tokens=40, min_tokens=1, overlap_tokens=5)

    assert chunks
    assert all("chunk_type" in c for c in chunks)
    assert all(c["char_end"] >= c["char_start"] for c in chunks)
    assert all(c["block_end_idx"] >= c["block_start_idx"] for c in chunks)


def test_insert_chunks_writes_metadata_columns_positive(monkeypatch):
    db = FakeDb()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    document_id = uuid.uuid4()
    source_version_id = uuid.uuid4()

    class FakeSettings:
        CHUNK_TARGET_TOKENS = 650
        CHUNK_MAX_TOKENS = 900
        CHUNK_MIN_TOKENS = 120
        CHUNK_OVERLAP_TOKENS = 80

    monkeypatch.setattr("app.services.ingestion._load_settings", lambda: FakeSettings())

    from app.services.ingestion import _insert_chunks

    chunk_ids = _insert_chunks(db, tenant, document_id, source_version_id, "# T\n\ntext body")
    assert chunk_ids
    insert_calls = [x for x in db.calls if "INSERT INTO chunks" in x[0]]
    assert insert_calls
    params = insert_calls[0][1]
    assert "chunk_type" in params
    assert "char_start" in params
    assert "char_end" in params
    assert "block_start_idx" in params
    assert "block_end_idx" in params
