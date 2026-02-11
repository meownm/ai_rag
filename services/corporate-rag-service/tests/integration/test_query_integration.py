import json
import uuid
from datetime import datetime, timezone

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.services.reranker import RerankerService


class FakeModel:
    def predict(self, pairs):
        return [0.1 for _ in pairs]


class FakeChunk:
    def __init__(self, text: str, ordinal: int, tenant_id: str, document_id: uuid.UUID):
        self.chunk_id = uuid.uuid4()
        self.document_id = document_id
        self.chunk_text = text
        self.chunk_path = "Policy/Section"
        self.ordinal = ordinal
        self.tenant_id = tenant_id


class FakeDocument:
    def __init__(self, title: str, document_id: uuid.UUID):
        self.document_id = document_id
        self.title = title
        self.url = "https://example.local/doc"
        self.labels = ["hr"]
        self.author = "Team"
        self.updated_date = datetime.now(timezone.utc)


class FakeVector:
    def __init__(self, emb):
        self.embedding = emb


class FakeMappings:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeExecResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return FakeMappings(self.rows)


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return None

    def join(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def all(self):
        return self.rows


class FakeDB:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, statement, *_args, **_kwargs):
        sql = str(statement)
        if "FROM chunk_fts" in sql:
            return FakeExecResult([{"chunk_id": str(self.rows[0][0].chunk_id), "lex_score": 0.9}])
        if "FROM chunk_vectors cv" in sql:
            return FakeExecResult([
                {"chunk_id": str(self.rows[0][0].chunk_id), "distance": 0.1, "vec_score": 0.91},
                {"chunk_id": str(self.rows[1][0].chunk_id), "distance": 0.8, "vec_score": 0.55},
            ])
        return FakeExecResult([])

    def add(self, _obj):
        return None

    def commit(self):
        return None

    def refresh(self, _obj):
        return None

    def query(self, model):
        if getattr(model, "__name__", "") == "IngestJobs":
            return FakeQuery([])
        return FakeQuery(self.rows)


def override_db_with_rows(rows):
    def _dep():
        yield FakeDB(rows)

    return _dep


def test_query_endpoint_with_llm_success(monkeypatch):
    from app.api import routes

    doc = uuid.uuid4()
    rows = [
        (FakeChunk("Corporate policy requires annual security training completion.", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Security Policy", doc), FakeVector([0.9, 0.1, 0.0])),
        (FakeChunk("Vacation policy includes 28 calendar days for full-time employees.", 2, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("HR Policy", doc), FakeVector([0.1, 0.8, 0.2])),
    ]
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.8, 0.2, 0.0]

    class FakeOllamaClient:
        def generate(self, *_args, **_kwargs):
            return {"response": json.dumps({"status": "success", "answer": "Vacation policy allows 28 days [chunk].", "citations": [{"chunk_id": str(rows[1][0].chunk_id), "quote": "28 calendar days"}]})}

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_ollama_client", lambda: FakeOllamaClient())
    monkeypatch.setattr(routes, "verify_answer", lambda *_a, **_k: (True, {"refusal_triggered": False}))

    app.dependency_overrides[get_db] = override_db_with_rows(rows)
    client = TestClient(app)
    response = client.post("/v1/query", json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "vacation policy", "citations": True, "top_k": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["only_sources_verdict"] == "PASS"
    assert body["citations"]


def test_query_endpoint_malformed_llm_json_refusal(monkeypatch):
    from app.api import routes

    doc = uuid.uuid4()
    rows = [(FakeChunk("context", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.1, 0.2]))]
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.8, 0.2]

    class BadOllamaClient:
        def generate(self, *_args, **_kwargs):
            return {"response": "not-json"}

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_ollama_client", lambda: BadOllamaClient())
    app.dependency_overrides[get_db] = override_db_with_rows(rows)
    client = TestClient(app)
    response = client.post("/v1/query", json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "x", "top_k": 1})
    assert response.status_code == 200
    assert response.json()["only_sources_verdict"] == "FAIL"


def test_query_endpoint_empty_citations_refusal(monkeypatch):
    from app.api import routes

    doc = uuid.uuid4()
    rows = [(FakeChunk("context", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.1, 0.2]))]
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.8, 0.2]

    class EmptyCitationOllama:
        def generate(self, *_args, **_kwargs):
            return {"response": json.dumps({"status": "success", "answer": "x", "citations": []})}

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_ollama_client", lambda: EmptyCitationOllama())
    app.dependency_overrides[get_db] = override_db_with_rows(rows)
    client = TestClient(app)
    response = client.post("/v1/query", json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "x", "top_k": 1})
    assert response.status_code == 200
    assert response.json()["only_sources_verdict"] == "FAIL"


def test_query_endpoint_non_dict_llm_payload_refusal(monkeypatch):
    from app.api import routes

    doc = uuid.uuid4()
    rows = [(FakeChunk("context", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.1, 0.2]))]
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.8, 0.2]

    class StringOllama:
        def generate(self, *_args, **_kwargs):
            return "plain-text-response"

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_ollama_client", lambda: StringOllama())
    app.dependency_overrides[get_db] = override_db_with_rows(rows)
    client = TestClient(app)
    response = client.post("/v1/query", json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "x", "top_k": 1})
    assert response.status_code == 200
    assert response.json()["only_sources_verdict"] == "FAIL"
