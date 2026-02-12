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
        self.added = []
        self.conversation_turns = []
        self.query_resolutions = []
        self.conversation_summaries = []

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
        self.added.append(_obj)
        name = _obj.__class__.__name__
        if name == "ConversationTurns":
            self.conversation_turns.append(_obj)
        elif name == "QueryResolutions":
            self.query_resolutions.append(_obj)
        elif name == "ConversationSummaries":
            self.conversation_summaries.append(_obj)
        return None

    def commit(self):
        return None

    def refresh(self, _obj):
        return None

    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "IngestJobs":
            return FakeQuery([])
        if name == "ConversationTurns":
            return FakeQuery(self.conversation_turns)
        if name == "QueryResolutions":
            return FakeQuery(self.query_resolutions)
        if name == "ConversationSummaries":
            return FakeQuery(self.conversation_summaries)
        return FakeQuery(self.rows)


def override_db_with_rows(rows, holder=None):
    def _dep():
        db = FakeDB(rows)
        if holder is not None:
            holder["db"] = db
        yield db

    return _dep


def test_query_endpoint_with_llm_success(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", True)

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

    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", True)

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

    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", True)

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

    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", True)

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


def test_query_trace_contains_raw_and_norm_scores_when_flag_on(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", True)

    doc = uuid.uuid4()
    rows = [
        (FakeChunk("alpha policy", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc A", doc), FakeVector([0.9, 0.1])),
        (FakeChunk("beta policy", 2, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc B", doc), FakeVector([0.1, 0.9])),
    ]
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))
    monkeypatch.setattr(routes.settings, "HYBRID_SCORE_NORMALIZATION", True)

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.9, 0.1]

    class FakeOllamaClient:
        def generate(self, *_args, **_kwargs):
            return {"response": json.dumps({"status": "success", "answer": "ok", "citations": [{"chunk_id": str(rows[0][0].chunk_id), "quote": "alpha"}]})}

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_ollama_client", lambda: FakeOllamaClient())
    monkeypatch.setattr(routes, "verify_answer", lambda *_a, **_k: (True, {"refusal_triggered": False}))

    app.dependency_overrides[get_db] = override_db_with_rows(rows)
    client = TestClient(app)
    response = client.post("/v1/query", json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "policy", "top_k": 2})
    assert response.status_code == 200
    scoring_trace = response.json()["trace"]["scoring_trace"]
    assert scoring_trace
    assert "lex_raw" in scoring_trace[0]
    assert "lex_norm" in scoring_trace[0]
    assert "vec_raw" in scoring_trace[0]
    assert "vec_norm" in scoring_trace[0]


def test_query_returns_expanded_sources_when_contextual_expansion_on(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", True)

    doc = uuid.uuid4()
    rows = [
        (FakeChunk("base context", 2, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.9, 0.1])),
        (FakeChunk("prev context", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.85, 0.1])),
        (FakeChunk("next context", 3, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.8, 0.1])),
    ]
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))
    monkeypatch.setattr(routes.settings, "USE_CONTEXTUAL_EXPANSION", True)
    monkeypatch.setattr(routes.settings, "NEIGHBOR_WINDOW", 1)

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.9, 0.1]

    class FakeOllamaClient:
        def generate(self, *_args, **_kwargs):
            return {
                "response": json.dumps(
                    {
                        "status": "success",
                        "answer": "ok",
                        "citations": [{"chunk_id": str(rows[0][0].chunk_id), "quote": "base"}],
                    }
                )
            }

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_ollama_client", lambda: FakeOllamaClient())
    monkeypatch.setattr(routes, "verify_answer", lambda *_a, **_k: (True, {"refusal_triggered": False}))

    app.dependency_overrides[get_db] = override_db_with_rows(rows)
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "context", "top_k": 1, "citations": True},
    )

    assert response.status_code == 200
    citations = response.json()["citations"]
    assert len(citations) >= 2


def test_query_endpoint_flag_off_returns_retrieval_only_answer(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", False)
    monkeypatch.setattr(routes.settings, "MAX_CLARIFICATION_DEPTH", 2)

    doc = uuid.uuid4()
    rows = [
        (FakeChunk("first chunk text", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.9, 0.1])),
        (FakeChunk("second chunk text", 2, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.8, 0.2])),
        (FakeChunk("third chunk text", 3, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.7, 0.3])),
    ]
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.9, 0.1]

    class FailingOllamaClient:
        def generate(self, *_args, **_kwargs):
            raise AssertionError("LLM client should not be called when flag is disabled")

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_ollama_client", lambda: FailingOllamaClient())

    app.dependency_overrides[get_db] = override_db_with_rows(rows)
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "policy", "top_k": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["only_sources_verdict"] == "PASS"
    assert payload["answer"] == "first chunk text\n\nsecond chunk text"


def test_query_endpoint_passes_keep_alive_zero_to_llm(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", True)

    doc = uuid.uuid4()
    rows = [(FakeChunk("context", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.1, 0.2]))]
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.8, 0.2]

    class KeepAliveAssertingOllama:
        def generate(self, *_args, **kwargs):
            assert kwargs.get("keep_alive") == 0
            return {"response": json.dumps({"status": "success", "answer": "x", "citations": [{"chunk_id": str(rows[0][0].chunk_id), "quote": "context"}]})}

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_ollama_client", lambda: KeepAliveAssertingOllama())
    monkeypatch.setattr(routes, "verify_answer", lambda *_a, **_k: (True, {"refusal_triggered": False}))

    app.dependency_overrides[get_db] = override_db_with_rows(rows)
    client = TestClient(app)
    response = client.post("/v1/query", json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "x", "top_k": 1})

    assert response.status_code == 200
    assert response.json()["only_sources_verdict"] == "PASS"


def test_query_with_invalid_conversation_header_returns_400(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_CONVERSATION_MEMORY", True)

    doc = uuid.uuid4()
    rows = [(FakeChunk("context", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.1, 0.2]))]

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.8, 0.2]

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())

    app.dependency_overrides[get_db] = override_db_with_rows(rows)
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "x", "top_k": 1},
        headers={"X-Conversation-Id": "not-a-uuid"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "B-CONV-ID-INVALID"


def test_query_stateless_mode_does_not_write_conversation_tables(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_CONVERSATION_MEMORY", False)
    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", False)
    monkeypatch.setattr(routes.settings, "MAX_CLARIFICATION_DEPTH", 2)

    doc = uuid.uuid4()
    rows = [(FakeChunk("context", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.1, 0.2]))]
    holder = {}

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.8, 0.2]

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    app.dependency_overrides[get_db] = override_db_with_rows(rows, holder=holder)
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "x", "top_k": 1},
        headers={"X-Conversation-Id": "11111111-1111-1111-1111-111111111111"},
    )

    assert response.status_code == 200
    added_names = {obj.__class__.__name__ for obj in holder["db"].added}
    assert "Conversations" not in added_names
    assert "ConversationTurns" not in added_names


def test_query_memory_mode_persists_user_and_assistant_turns(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_CONVERSATION_MEMORY", True)
    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", False)
    monkeypatch.setattr(routes.settings, "MAX_CLARIFICATION_DEPTH", 2)

    doc = uuid.uuid4()
    rows = [(FakeChunk("context", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.1, 0.2]))]
    holder = {}

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.8, 0.2]

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    app.dependency_overrides[get_db] = override_db_with_rows(rows, holder=holder)
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "x", "top_k": 1},
        headers={
            "X-Conversation-Id": "11111111-1111-1111-1111-111111111111",
            "X-Client-Turn-Id": "22222222-2222-2222-2222-222222222222",
        },
    )

    assert response.status_code == 200
    added = holder["db"].added
    added_names = [obj.__class__.__name__ for obj in added]
    assert "Conversations" in added_names
    turn_objects = [obj for obj in added if obj.__class__.__name__ == "ConversationTurns"]
    assert len(turn_objects) == 2
    assert turn_objects[0].role == "user"
    assert turn_objects[1].role == "assistant"


def test_query_rewrite_flag_on_uses_resolved_query_for_embeddings(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_CONVERSATION_MEMORY", True)
    monkeypatch.setattr(routes.settings, "USE_LLM_QUERY_REWRITE", True)
    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", False)
    monkeypatch.setattr(routes.settings, "MAX_CLARIFICATION_DEPTH", 2)

    doc = uuid.uuid4()
    rows = [(FakeChunk("context", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.1, 0.2]))]
    holder = {}

    class FakeEmbeddingsClient:
        def __init__(self):
            self.queries = []

        def embed_text(self, query, *_args, **_kwargs):
            self.queries.append(query)
            return [0.8, 0.2]

    emb = FakeEmbeddingsClient()

    class FakeRewriteResult:
        resolved_query_text = "resolved vacation policy"
        confidence = 0.88
        topic_shift = False
        clarification_needed = False
        clarification_question = None

    class FakeRewriter:
        def rewrite(self, **_kwargs):
            return FakeRewriteResult()

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: emb)
    monkeypatch.setattr(routes, "get_query_rewriter", lambda: FakeRewriter())
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    app.dependency_overrides[get_db] = override_db_with_rows(rows, holder=holder)
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "vacation?", "top_k": 1},
        headers={"X-Conversation-Id": "11111111-1111-1111-1111-111111111111"},
    )

    assert response.status_code == 200
    assert emb.queries[0] == "resolved vacation policy"
    added_names = [obj.__class__.__name__ for obj in holder["db"].added]
    assert "QueryResolutions" in added_names


def test_query_rewrite_failure_returns_502(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_LLM_QUERY_REWRITE", True)
    monkeypatch.setattr(routes.settings, "USE_CONVERSATION_MEMORY", False)

    doc = uuid.uuid4()
    rows = [(FakeChunk("context", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.1, 0.2]))]

    class FailingRewriter:
        def rewrite(self, **_kwargs):
            raise ValueError("bad rewrite")

    monkeypatch.setattr(routes, "get_query_rewriter", lambda: FailingRewriter())

    app.dependency_overrides[get_db] = override_db_with_rows(rows)
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "x", "top_k": 1},
    )

    assert response.status_code == 502
    assert response.json()["detail"]["error"]["code"] == "B-REWRITE-FAILED"


def test_memory_boosting_increases_rank_for_recent_answer_chunk():
    from app.api import routes

    class Prev:
        used_in_answer = True
        document_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        chunk_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    candidates = [
        {"document_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "chunk_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "final_score": 0.2},
        {"document_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "chunk_id": "cccccccc-cccc-cccc-cccc-cccccccccccc", "final_score": 0.25},
    ]

    boosted, boosted_count = routes._apply_memory_boosting(candidates, [Prev()], max_boost=0.12)

    assert boosted_count == 1
    assert boosted[0]["chunk_id"] == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def test_memory_boosting_respects_cap():
    from app.api import routes

    class Prev:
        used_in_answer = True
        document_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        chunk_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    candidates = [
        {"document_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "chunk_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "final_score": 0.9},
    ]

    boosted, _ = routes._apply_memory_boosting(candidates, [Prev(), Prev(), Prev()], max_boost=0.05)

    boost_values = [b["value"] for b in boosted[0].get("boosts_applied", []) if b.get("name") == "memory_reuse_boost"]
    assert boost_values
    assert max(boost_values) <= 0.05


def test_clarification_turn_returns_question_without_retrieval(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_CONVERSATION_MEMORY", True)
    monkeypatch.setattr(routes.settings, "USE_LLM_QUERY_REWRITE", True)
    monkeypatch.setattr(routes.settings, "USE_CLARIFICATION_LOOP", True)
    monkeypatch.setattr(routes.settings, "REWRITE_CONFIDENCE_THRESHOLD", 0.55)

    class ClarifyDB(FakeDB):
        def execute(self, *_args, **_kwargs):
            raise AssertionError("retrieval should not run during clarification turn")

    class FakeRewriteResult:
        resolved_query_text = "ambiguous request"
        confidence = 0.2
        topic_shift = False
        clarification_needed = True
        clarification_question = "Do you mean paid vacation policy or unpaid leave policy?"

    class FakeRewriter:
        def rewrite(self, **_kwargs):
            return FakeRewriteResult()

    holder = {}

    def _dep():
        db = ClarifyDB([])
        holder["db"] = db
        yield db

    monkeypatch.setattr(routes, "get_query_rewriter", lambda: FakeRewriter())

    app.dependency_overrides[get_db] = _dep
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "leave", "top_k": 1},
        headers={"X-Conversation-Id": "11111111-1111-1111-1111-111111111111"},
    )

    assert response.status_code == 200
    assert "Do you mean" in response.json()["answer"]
    names = [obj.__class__.__name__ for obj in holder["db"].added]
    assert "QueryResolutions" in names
    assert "ConversationTurns" in names


def test_clarification_followup_exceeding_depth_returns_controlled_fallback(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_CONVERSATION_MEMORY", True)
    monkeypatch.setattr(routes.settings, "USE_LLM_QUERY_REWRITE", True)
    monkeypatch.setattr(routes.settings, "USE_CLARIFICATION_LOOP", True)
    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", False)
    monkeypatch.setattr(routes.settings, "MAX_CLARIFICATION_DEPTH", 2)

    doc = uuid.uuid4()
    rows = [(FakeChunk("context", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.1, 0.2]))]

    class FakeRewriteResult:
        resolved_query_text = "resolved policy"
        confidence = 0.1
        topic_shift = False
        clarification_needed = True
        clarification_question = "Need more details?"

    class FakeRewriter:
        def rewrite(self, **kwargs):
            assert kwargs.get("clarification_pending") is True
            return FakeRewriteResult()

    class ClarifyStreakDB(FakeDB):
        def query(self, model):
            name = getattr(model, "__name__", "")
            if name == "QueryResolutions":
                q = FakeQuery([type("R", (), {"needs_clarification": True, "clarification_question": "q1"})(), type("R", (), {"needs_clarification": True, "clarification_question": "q2"})()])
                q.first = lambda: type("R", (), {"needs_clarification": True, "clarification_question": "q2"})()
                return q
            return super().query(model)

    def _dep():
        yield ClarifyStreakDB(rows)

    monkeypatch.setattr(routes, "get_query_rewriter", lambda: FakeRewriter())
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.8, 0.2]

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())

    app.dependency_overrides[get_db] = _dep
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "it", "top_k": 1},
        headers={"X-Conversation-Id": "11111111-1111-1111-1111-111111111111"},
    )

    assert response.status_code == 200
    assert "недостаточно информации" in response.json()["answer"].lower()




def test_clarification_depth_exact_limit_still_asks_question(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_CONVERSATION_MEMORY", True)
    monkeypatch.setattr(routes.settings, "USE_LLM_QUERY_REWRITE", True)
    monkeypatch.setattr(routes.settings, "USE_CLARIFICATION_LOOP", True)
    monkeypatch.setattr(routes.settings, "MAX_CLARIFICATION_DEPTH", 2)

    class FakeRewriteResult:
        resolved_query_text = "resolved policy"
        confidence = 0.1
        topic_shift = False
        clarification_needed = True
        clarification_question = "Need one more detail?"

    class FakeRewriter:
        def rewrite(self, **kwargs):
            assert kwargs.get("clarification_pending") is True
            return FakeRewriteResult()

    class ClarifyStreakDB(FakeDB):
        def query(self, model):
            name = getattr(model, "__name__", "")
            if name == "QueryResolutions":
                q = FakeQuery([type("R", (), {"needs_clarification": True, "clarification_question": "q1"})()])
                q.first = lambda: type("R", (), {"needs_clarification": True, "clarification_question": "q1"})()
                return q
            return super().query(model)

    def _dep():
        yield ClarifyStreakDB([])

    monkeypatch.setattr(routes, "get_query_rewriter", lambda: FakeRewriter())

    app.dependency_overrides[get_db] = _dep
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "it", "top_k": 1},
        headers={"X-Conversation-Id": "11111111-1111-1111-1111-111111111111"},
    )

    assert response.status_code == 200
    assert "Need one more detail" in response.json()["answer"]


def test_summary_created_after_threshold(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_CONVERSATION_MEMORY", True)
    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", False)
    monkeypatch.setattr(routes.settings, "MAX_CLARIFICATION_DEPTH", 2)
    monkeypatch.setattr(routes.settings, "CONVERSATION_SUMMARY_THRESHOLD_TURNS", 1)

    doc = uuid.uuid4()
    rows = [(FakeChunk("context", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.1, 0.2]))]
    holder = {}

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.8, 0.2]

    class FakeSummarizer:
        def summarize(self, *_args, **_kwargs):
            return "Conversation summary for rewriting"

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))
    monkeypatch.setattr(routes, "get_conversation_summarizer", lambda: FakeSummarizer())

    app.dependency_overrides[get_db] = override_db_with_rows(rows, holder=holder)
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "x", "top_k": 1},
        headers={"X-Conversation-Id": "11111111-1111-1111-1111-111111111111"},
    )

    assert response.status_code == 200
    names = [obj.__class__.__name__ for obj in holder["db"].added]
    assert "ConversationSummaries" in names


def test_summary_masked_mode_does_not_store_quotes(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_CONVERSATION_MEMORY", True)
    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", False)
    monkeypatch.setattr(routes.settings, "MAX_CLARIFICATION_DEPTH", 2)
    monkeypatch.setattr(routes.settings, "CONVERSATION_SUMMARY_THRESHOLD_TURNS", 1)
    monkeypatch.setattr(routes.settings, "LOG_DATA_MODE", "MASKED")

    doc = uuid.uuid4()
    rows = [(FakeChunk("context", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.1, 0.2]))]
    holder = {}

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.8, 0.2]

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    app.dependency_overrides[get_db] = override_db_with_rows(rows, holder=holder)
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "secret is 12345", "top_k": 1},
        headers={"X-Conversation-Id": "11111111-1111-1111-1111-111111111111"},
    )

    assert response.status_code == 200
    summaries = [obj for obj in holder["db"].added if obj.__class__.__name__ == "ConversationSummaries"]
    assert summaries
    assert "\"" not in summaries[-1].summary_text
    assert "12345" not in summaries[-1].summary_text


def test_rewriter_receives_latest_summary_when_present(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_CONVERSATION_MEMORY", True)
    monkeypatch.setattr(routes.settings, "USE_LLM_QUERY_REWRITE", True)
    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", False)
    monkeypatch.setattr(routes.settings, "MAX_CLARIFICATION_DEPTH", 2)

    doc = uuid.uuid4()
    rows = [(FakeChunk("context", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.1, 0.2]))]

    captured = {}

    class FakeRewriteResult:
        resolved_query_text = "resolved"
        confidence = 0.9
        topic_shift = False
        clarification_needed = False
        clarification_question = None

    class FakeRewriter:
        def rewrite(self, **kwargs):
            captured["summary"] = kwargs.get("summary")
            return FakeRewriteResult()

    class SummaryAwareDB(FakeDB):
        def __init__(self, rows):
            super().__init__(rows)
            self.conversation_summaries = [
                type(
                    "S",
                    (),
                    {
                        "summary_text": "Existing conversation summary",
                        "summary_version": 1,
                        "covers_turn_index_to": 2,
                    },
                )()
            ]

    def _dep():
        yield SummaryAwareDB(rows)

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.8, 0.2]

    monkeypatch.setattr(routes, "get_query_rewriter", lambda: FakeRewriter())
    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    app.dependency_overrides[get_db] = _dep
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "x", "top_k": 1},
        headers={"X-Conversation-Id": "11111111-1111-1111-1111-111111111111"},
    )

    assert response.status_code == 200
    assert captured["summary"] == "Existing conversation summary"


def test_clarification_signal_ignored_when_loop_flag_disabled(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_CONVERSATION_MEMORY", True)
    monkeypatch.setattr(routes.settings, "USE_LLM_QUERY_REWRITE", True)
    monkeypatch.setattr(routes.settings, "USE_CLARIFICATION_LOOP", False)
    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", False)
    monkeypatch.setattr(routes.settings, "MAX_CLARIFICATION_DEPTH", 2)

    doc = uuid.uuid4()
    rows = [(FakeChunk("context", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.1, 0.2]))]

    class FakeRewriteResult:
        resolved_query_text = "resolved"
        confidence = 0.1
        topic_shift = False
        clarification_needed = True
        clarification_question = "Need clarification?"

    class FakeRewriter:
        def rewrite(self, **_kwargs):
            return FakeRewriteResult()

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.8, 0.2]

    monkeypatch.setattr(routes, "get_query_rewriter", lambda: FakeRewriter())
    class FakeOllamaLowConfidence:
        def generate(self, *_args, **_kwargs):
            return {"response": '{"status":"success","answer":"generated","citations":[{"chunk_id":"x","quote":"q"}]}' }

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))
    monkeypatch.setattr(routes, "get_ollama_client", lambda: FakeOllamaLowConfidence())

    app.dependency_overrides[get_db] = override_db_with_rows(rows)
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "x", "top_k": 1},
        headers={"X-Conversation-Id": "11111111-1111-1111-1111-111111111111"},
    )

    assert response.status_code == 200
    assert "недостаточно информации" in response.json()["answer"].lower()


def test_summary_not_created_below_threshold(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_CONVERSATION_MEMORY", True)
    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", False)
    monkeypatch.setattr(routes.settings, "MAX_CLARIFICATION_DEPTH", 2)
    monkeypatch.setattr(routes.settings, "CONVERSATION_SUMMARY_THRESHOLD_TURNS", 50)

    doc = uuid.uuid4()
    rows = [(FakeChunk("context", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.1, 0.2]))]
    holder = {}

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.8, 0.2]

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    app.dependency_overrides[get_db] = override_db_with_rows(rows, holder=holder)
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "x", "top_k": 1},
        headers={"X-Conversation-Id": "11111111-1111-1111-1111-111111111111"},
    )

    assert response.status_code == 200
    summaries = [obj for obj in holder["db"].added if obj.__class__.__name__ == "ConversationSummaries"]
    assert summaries == []


def test_stage_latency_metrics_are_emitted(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", False)
    monkeypatch.setattr(routes.settings, "ENABLE_PER_STAGE_LATENCY_METRICS", True)

    doc = uuid.uuid4()
    rows = [(FakeChunk("context", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.1, 0.2]))]

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.8, 0.2]

    stage_calls = []
    metric_calls = []

    def _capture_stage(**kwargs):
        stage_calls.append(kwargs)

    def _capture_metric(name, value):
        metric_calls.append((name, value))

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))
    monkeypatch.setattr(routes, "log_stage_latency", _capture_stage)
    monkeypatch.setattr(routes, "emit_metric", _capture_metric)

    app.dependency_overrides[get_db] = override_db_with_rows(rows)
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "policy", "top_k": 1},
    )

    assert response.status_code == 200
    observed = {call["stage"] for call in stage_calls}
    assert {"retrieval_agent", "analysis_agent", "answer_agent"}.issubset(observed)
    assert any(name == "rag_retrieval_latency" for name, _ in metric_calls)
    assert any(name == "rag_analysis_latency" for name, _ in metric_calls)
    assert any(name == "rag_answer_latency" for name, _ in metric_calls)


def test_low_confidence_fallback_triggered_below_threshold(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", True)
    monkeypatch.setattr(routes.settings, "CONFIDENCE_FALLBACK_THRESHOLD", 0.3)

    doc = uuid.uuid4()
    rows = [(FakeChunk("completely unrelated corpus", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.0, 0.0]))]

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.0, 0.0]

    class FakeOllamaLowConfidence:
        def generate(self, *_args, **_kwargs):
            return {"response": '{"status":"success","answer":"generated","citations":[{"chunk_id":"x","quote":"q"}]}' }

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))
    monkeypatch.setattr(routes, "get_ollama_client", lambda: FakeOllamaLowConfidence())

    app.dependency_overrides[get_db] = override_db_with_rows(rows)
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "vacation policy", "top_k": 1},
    )

    assert response.status_code == 200
    assert "недостаточно информации" in response.json()["answer"].lower()


def test_low_confidence_fallback_not_triggered_on_threshold_boundary(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", True)
    monkeypatch.setattr(routes.settings, "CONFIDENCE_FALLBACK_THRESHOLD", 0.05)

    doc = uuid.uuid4()
    rows = [(FakeChunk("irrelevant", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Doc", doc), FakeVector([0.0, 0.0]))]

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.0, 0.0]

    class FakeOllamaBoundary:
        def generate(self, *_args, **_kwargs):
            return {"response": '{"status":"success","answer":"generated","citations":[{"chunk_id":"x","quote":"q"}]}' }

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())
    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))
    monkeypatch.setattr(routes, "get_ollama_client", lambda: FakeOllamaBoundary())

    app.dependency_overrides[get_db] = override_db_with_rows(rows)
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "vacation policy", "top_k": 1},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "generated"


def test_query_requests_pass_through_agent_pipeline(monkeypatch):
    from app.api import routes
    from app.services.agent_pipeline import AgentPipelineResult, AgentStageTrace

    monkeypatch.setattr(routes.settings, "USE_LLM_GENERATION", False)

    doc = uuid.uuid4()
    rows = [
        (FakeChunk("Vacation policy includes 28 calendar days for full-time employees.", 2, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("HR Policy", doc), FakeVector([0.1, 0.8, 0.2])),
        (FakeChunk("Security training is mandatory.", 1, "11111111-1111-1111-1111-111111111111", doc), FakeDocument("Security Policy", doc), FakeVector([0.9, 0.1, 0.0])),
    ]

    monkeypatch.setattr(routes, "get_reranker", lambda: RerankerService("fake", model=FakeModel()))

    class FakeEmbeddingsClient:
        def embed_text(self, *_args, **_kwargs):
            return [0.8, 0.2, 0.0]

    monkeypatch.setattr(routes, "get_embeddings_client", lambda: FakeEmbeddingsClient())

    called = {"value": False}

    class SpyPipeline:
        def run(self, request):
            called["value"] = True
            rewrite = request.rewrite_input.execute(request.query)
            ranked = request.retrieval_input.execute(rewrite["resolved_query_text"])["ranked_candidates"]
            analysis = request.analysis_input_builder(ranked).execute(ranked)
            answer_data = request.answer_input_builder(analysis["selected_candidates"]).execute(request.query, analysis["selected_candidates"])
            return AgentPipelineResult(
                answer=answer_data["answer"],
                only_sources_verdict=answer_data["only_sources_verdict"],
                selected_candidates=analysis["selected_candidates"],
                confidence=float(analysis["confidence"]),
                needs_clarification=False,
                clarification_question=None,
                fallback_reason=None,
                stage_traces=[AgentStageTrace(stage="rewrite_agent", latency_ms=1, output={})],
            )

    monkeypatch.setattr(routes, "get_agent_pipeline", lambda: SpyPipeline())

    app.dependency_overrides[get_db] = override_db_with_rows(rows)
    client = TestClient(app)
    response = client.post("/v1/query", json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "vacation policy", "citations": True, "top_k": 2})

    assert response.status_code == 200
    assert called["value"] is True


def test_clarification_path_passes_through_agent_pipeline(monkeypatch):
    from app.api import routes
    from app.services.agent_pipeline import AgentPipelineResult, AgentStageTrace

    monkeypatch.setattr(routes.settings, "USE_CONVERSATION_MEMORY", True)
    monkeypatch.setattr(routes.settings, "USE_LLM_QUERY_REWRITE", True)
    monkeypatch.setattr(routes.settings, "USE_CLARIFICATION_LOOP", True)
    monkeypatch.setattr(routes.settings, "REWRITE_CONFIDENCE_THRESHOLD", 0.55)

    class ClarifyDB(FakeDB):
        def execute(self, *_args, **_kwargs):
            raise AssertionError("retrieval should not run during clarification turn")

    class FakeRewriteResult:
        resolved_query_text = "ambiguous request"
        confidence = 0.2
        topic_shift = False
        clarification_needed = True
        clarification_question = "Уточните подразделение?"

    class FakeRewriter:
        def rewrite(self, **_kwargs):
            return FakeRewriteResult()

    called = {"value": False}

    class SpyPipeline:
        def run(self, request):
            called["value"] = True
            rewrite = request.rewrite_input.execute(request.query)
            assert rewrite["clarification_needed"] is True
            assert request.clarification_depth == 1
            return AgentPipelineResult(
                answer="Уточните подразделение?",
                only_sources_verdict="PASS",
                selected_candidates=[],
                confidence=0.2,
                needs_clarification=True,
                clarification_question="Уточните подразделение?",
                fallback_reason=None,
                stage_traces=[AgentStageTrace(stage="rewrite_agent", latency_ms=1, output={})],
            )

    holder = {}

    def _dep():
        db = ClarifyDB([])
        holder["db"] = db
        yield db

    monkeypatch.setattr(routes, "get_query_rewriter", lambda: FakeRewriter())
    monkeypatch.setattr(routes, "get_agent_pipeline", lambda: SpyPipeline())

    app.dependency_overrides[get_db] = _dep
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "leave", "top_k": 1},
        headers={"X-Conversation-Id": "11111111-1111-1111-1111-111111111111"},
    )

    assert response.status_code == 200
    assert called["value"] is True
    assert "Уточните" in response.json()["answer"]


def test_clarification_depth_exceeded_pipeline_logs_explicit_error(monkeypatch):
    from app.api import routes
    from app.services.agent_pipeline import AgentPipelineResult, AgentStageTrace

    monkeypatch.setattr(routes.settings, "USE_CONVERSATION_MEMORY", True)
    monkeypatch.setattr(routes.settings, "USE_LLM_QUERY_REWRITE", True)
    monkeypatch.setattr(routes.settings, "USE_CLARIFICATION_LOOP", True)
    monkeypatch.setattr(routes.settings, "MAX_CLARIFICATION_DEPTH", 2)

    class FakeRewriteResult:
        resolved_query_text = "ambiguous request"
        confidence = 0.1
        topic_shift = False
        clarification_needed = True
        clarification_question = "Need more details?"

    class FakeRewriter:
        def rewrite(self, **_kwargs):
            return FakeRewriteResult()

    class ClarifyStreakDB(FakeDB):
        def query(self, model):
            name = getattr(model, "__name__", "")
            if name == "QueryResolutions":
                q = FakeQuery([type("R", (), {"needs_clarification": True, "clarification_question": "q1"})(), type("R", (), {"needs_clarification": True, "clarification_question": "q2"})()])
                q.first = lambda: type("R", (), {"needs_clarification": True, "clarification_question": "q2"})()
                return q
            return super().query(model)

    called = {"value": False}
    events = []

    class SpyPipeline:
        def run(self, request):
            called["value"] = True
            assert request.clarification_depth == 3
            return AgentPipelineResult(
                answer="Похоже, недостаточно информации для ответа... Попробуйте уточнить вопрос и сузить область поиска.",
                only_sources_verdict="FAIL",
                selected_candidates=[],
                confidence=0.0,
                needs_clarification=False,
                clarification_question=None,
                fallback_reason="clarification_depth_exceeded",
                stage_traces=[AgentStageTrace(stage="rewrite_agent", latency_ms=1, output={})],
            )

    def _capture_log_event(db, tenant_id, correlation_id, event_type, payload, duration_ms=None):
        events.append((event_type, payload))
        return None

    monkeypatch.setattr(routes, "get_query_rewriter", lambda: FakeRewriter())
    monkeypatch.setattr(routes, "get_agent_pipeline", lambda: SpyPipeline())
    monkeypatch.setattr(routes, "log_event", _capture_log_event)

    def _dep():
        yield ClarifyStreakDB([])

    app.dependency_overrides[get_db] = _dep
    client = TestClient(app)
    response = client.post(
        "/v1/query",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "leave", "top_k": 1},
        headers={"X-Conversation-Id": "11111111-1111-1111-1111-111111111111"},
    )

    assert response.status_code == 200
    assert called["value"] is True
    assert response.json()["only_sources_verdict"] == "FAIL"
    assert any(event == "ERROR" and payload.get("code") == "RH-CLARIFICATION-DEPTH-EXCEEDED" for event, payload in events)
