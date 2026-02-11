import json
import uuid

import pytest
from datetime import datetime, timezone

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.services.reranker import RerankerService


class FakeModel:
    def predict(self, pairs):
        return [0.1, 0.99]


class FakeChunk:
    def __init__(self, text: str, ordinal: int, tenant_id: str):
        self.chunk_id = uuid.uuid4()
        self.document_id = uuid.uuid4()
        self.chunk_text = text
        self.chunk_path = "Policy/Section"
        self.ordinal = ordinal
        self.tenant_id = tenant_id


class FakeDocument:
    def __init__(self, title: str):
        self.document_id = uuid.uuid4()
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

    def execute(self, *_args, **_kwargs):
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


def test_query_endpoint_reranker_changes_order(monkeypatch):
    from app.api import routes

    rows = [
        (FakeChunk("Corporate policy requires annual security training completion.", 1, "11111111-1111-1111-1111-111111111111"), FakeDocument("Security Policy"), FakeVector([0.9, 0.1, 0.0])),
        (FakeChunk("Vacation policy includes 28 calendar days for full-time employees.", 2, "11111111-1111-1111-1111-111111111111"), FakeDocument("HR Policy"), FakeVector([0.1, 0.8, 0.2])),
    ]
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    class FakeEmbeddingsClient:
        def embed(self, *args, **kwargs):
            return [[0.8, 0.2, 0.0]]

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    app.dependency_overrides[get_db] = override_db_with_rows(rows)
    client = TestClient(app)
    payload = {
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "query": "vacation policy",
        "citations": True,
        "top_k": 2,
    }
    response = client.post("/v1/query", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["citations"][0]["title"] == "HR Policy"
    assert body["trace"]["trace_id"]
    assert body["trace"]["scoring_trace"][0]["lex_score"] >= 0
    assert body["trace"]["scoring_trace"][0]["vec_score"] >= 0
    assert "boosts_applied" in body["trace"]["scoring_trace"][0]


def test_query_endpoint_embeddings_failure(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    class BrokenEmbeddingsClient:
        def embed(self, *args, **kwargs):
            raise RuntimeError("embeddings down")

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: BrokenEmbeddingsClient())
    app.dependency_overrides[get_db] = override_db_with_rows([])
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "query": "vacation",
            "top_k": 1,
        },
    )
    assert response.status_code == 500


def test_query_endpoint_validation_negative(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    class FakeEmbeddingsClient:
        def embed(self, *args, **kwargs):
            return [[0.8, 0.2, 0.0]]

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    app.dependency_overrides[get_db] = override_db_with_rows([])
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "query": "bad",
            "top_k": 0,
        },
    )
    assert response.status_code == 422


def test_get_job_not_found_returns_contract_envelope(monkeypatch):
    app.dependency_overrides[get_db] = override_db_with_rows([])
    client = TestClient(app)
    response = client.get("/v1/jobs/11111111-1111-1111-1111-111111111111")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "SOURCE_NOT_FOUND"


def test_query_endpoint_hallucination_refusal_returns_structured_json(monkeypatch):
    from app.api import routes

    rows = [
        (FakeChunk("Corporate policy requires annual security training completion.", 1, "11111111-1111-1111-1111-111111111111"), FakeDocument("Security Policy"), FakeVector([0.9, 0.1, 0.0])),
    ]
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    class FakeEmbeddingsClient:
        def embed(self, *args, **kwargs):
            return [[0.8, 0.2, 0.0]]

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "verify_answer", lambda *_args, **_kwargs: (False, {"unsupported_sentences": 1}))

    app.dependency_overrides[get_db] = override_db_with_rows(rows)
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "query": "vacation",
            "top_k": 1,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["only_sources_verdict"] == "FAIL"
    refusal = json.loads(body["answer"])
    assert refusal["refusal"]["code"] == "ONLY_SOURCES_VIOLATION"
