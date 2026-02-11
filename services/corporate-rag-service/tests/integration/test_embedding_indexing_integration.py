import uuid

from app.services.ingestion import _upsert_chunk_vectors


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
        self.vectorized_chunk_ids = set()
        self.upsert_count = 0

    def execute(self, statement, params=None):
        stmt = str(statement)
        payload = params or {}

        if "SELECT c.chunk_id, c.chunk_text" in stmt and "LEFT JOIN chunk_vectors" in stmt:
            rows = []
            for chunk_id in payload.get("chunk_ids", []):
                if chunk_id not in self.vectorized_chunk_ids:
                    rows.append({"chunk_id": chunk_id, "chunk_text": f"chunk-{chunk_id}"})
            return FakeResult(rows)

        if "INSERT INTO chunk_vectors" in stmt:
            self.vectorized_chunk_ids.add(payload["chunk_id"])
            self.upsert_count += 1
            return FakeResult()

        return FakeResult()


class FakeSettings:
    EMBEDDINGS_BATCH_SIZE = 2
    EMBEDDINGS_RETRY_ATTEMPTS = 2
    EMBEDDINGS_DEFAULT_MODEL_ID = "bge-m3"
    EMBEDDINGS_SERVICE_URL = "http://localhost:8200"
    EMBEDDINGS_TIMEOUT_SECONDS = 30


class FakeEmbeddingsClient:
    calls = 0

    def __init__(self, *_args, **_kwargs):
        pass

    def embed_texts(self, texts, **_kwargs):
        FakeEmbeddingsClient.calls += 1
        return [[0.11, 0.22, 0.33] for _ in texts]


def test_embedding_indexing_upsert_is_idempotent(monkeypatch):
    FakeEmbeddingsClient.calls = 0
    db = FakeDb()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    chunk_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]

    monkeypatch.setattr("app.services.ingestion._load_settings", lambda: FakeSettings())
    monkeypatch.setattr("app.services.ingestion.EmbeddingsClient", FakeEmbeddingsClient)

    _upsert_chunk_vectors(db, tenant, chunk_ids)
    first_count = db.upsert_count
    first_calls = FakeEmbeddingsClient.calls

    _upsert_chunk_vectors(db, tenant, chunk_ids)
    second_count = db.upsert_count
    second_calls = FakeEmbeddingsClient.calls

    assert first_count == len(chunk_ids)
    assert second_count == first_count
    assert first_calls == 2
    assert second_calls == first_calls
