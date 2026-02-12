import json
import uuid
from datetime import datetime, timezone

import pytest



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
        self.labels = ["ops"]
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
        return self.rows[0] if self.rows else None

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
            return FakeExecResult([{"chunk_id": str(self.rows[0][0].chunk_id), "distance": 0.1, "vec_score": 0.91}])
        return FakeExecResult([])

    def add(self, _obj):
        return None

    def commit(self):
        return None

    def refresh(self, _obj):
        return None

    def query(self, _model):
        return FakeQuery(self.rows)


def _override_db(rows):
    def _dep():
        yield FakeDB(rows)

    return _dep


def _events(stderr: str) -> list[dict]:
    parsed = []
    for line in stderr.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return parsed


def _missing_required_events(events: list[dict]) -> set[str]:
    required = {"api.request.completed", "context.assembly", "llm.call.completed"}
    got = {event.get("event_type") for event in events}
    return required - got


def _event_schema_is_valid(event: dict) -> bool:
    required_types = {
        "ts": str,
        "service": str,
        "env": str,
        "event_type": str,
        "request_id": str,
        "plane": str,
        "version": str,
    }
    for key, expected_type in required_types.items():
        if key not in event or not isinstance(event[key], expected_type) or not event[key]:
            return False
    return True


def test_required_observability_events_emitted_with_schema(monkeypatch, capsys):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from app.api import routes
    from app.db.session import get_db
    from app.main import app
    from app.services.reranker import RerankerService

    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", True)

    doc_id = uuid.uuid4()
    rows = [
        (FakeChunk("Incident response policy", 1, "11111111-1111-1111-1111-111111111111", doc_id), FakeDocument("Ops policy", doc_id), FakeVector([0.9, 0.1]))
    ]

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.8, 0.2]

    class FakeOllamaClient:
        def generate(self, *_args, **_kwargs):
            return {
                "response": json.dumps(
                    {
                        "status": "success",
                        "answer": "Use incident process.",
                        "citations": [{"chunk_id": str(rows[0][0].chunk_id), "quote": "Incident response policy"}],
                    }
                )
            }

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_ollama_client", lambda: FakeOllamaClient())
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))
    monkeypatch.setattr(routes, "verify_answer", lambda *_a, **_k: (True, {"refusal_triggered": False}))

    app.dependency_overrides[get_db] = _override_db(rows)
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "incident", "top_k": 1, "citations": True},
    )

    assert response.status_code == 200
    events = _events(capsys.readouterr().err)

    required = {"api.request.completed", "context.assembly", "llm.call.completed"}
    assert not _missing_required_events(events)

    for event in events:
        if event.get("event_type") in required:
            assert _event_schema_is_valid(event)


def test_event_schema_validator_rejects_missing_request_id():
    invalid_event = {
        "ts": "2026-02-12T00:00:00Z",
        "service": "corporate-rag-service",
        "env": "local",
        "event_type": "api.request.completed",
        "plane": "data",
        "version": "1.0.0",
    }
    assert not _event_schema_is_valid(invalid_event)


def test_missing_required_events_detector_negative_case():
    events = [{"event_type": "api.request.completed"}, {"event_type": "context.assembly"}]
    missing = _missing_required_events(events)
    assert "llm.call.completed" in missing

