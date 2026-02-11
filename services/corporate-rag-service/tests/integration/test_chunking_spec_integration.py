import uuid

from app.services.ingestion import SourceItem, ingest_sources_sync


class FakeMappings:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeResult:
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
    def put_text(self, bucket: str, key: str, text: str) -> str:
        return f"s3://{bucket}/{key}"


class FakeConfluence:
    def crawl(self, tenant_id):
        return [
            SourceItem(
                source_type="CONFLUENCE_PAGE",
                external_ref="page:spec",
                title="Spec",
                markdown="# H1\n\nParagraph text for chunking.\n\n- item 1\n- item 2\n",
            )
        ]


def test_ingestion_populates_chunk_metadata_fields_integration(monkeypatch):
    db = FakeDb()
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
        ["CONFLUENCE_PAGE"],
        confluence=FakeConfluence(),
        storage=FakeStorage(),
    )

    assert result["documents"] == 1
    chunk_inserts = [x for x in db.calls if "INSERT INTO chunks" in x[0]]
    assert chunk_inserts
    params = chunk_inserts[0][1]
    assert params["chunk_type"] in {"paragraph", "list", "table", "code", "quote", "mixed"}
    assert isinstance(params["char_start"], int)
    assert isinstance(params["char_end"], int)
    assert isinstance(params["block_start_idx"], int)
    assert isinstance(params["block_end_idx"], int)
