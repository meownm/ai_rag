import uuid

import pytest

pytest.importorskip("sqlalchemy")

from app.db.repositories import ConversationRepository


class FakeQuery:
    def __init__(self, first_result=None):
        self.filters = []
        self.order_by_calls = []
        self.limit_value = None
        self.first_result = first_result

    def filter(self, criterion):
        self.filters.append(str(criterion))
        return self

    def order_by(self, *args):
        self.order_by_calls.extend(str(x) for x in args)
        return self

    def limit(self, limit_value):
        self.limit_value = limit_value
        return self

    def first(self):
        return self.first_result

    def all(self):
        return []


class FakeDB:
    def __init__(self, first_results=None):
        self.queries = []
        self.first_results = list(first_results or [])
        self.added = []
        self.commits = 0

    def query(self, *_args, **_kwargs):
        first_result = self.first_results.pop(0) if self.first_results else None
        query = FakeQuery(first_result=first_result)
        self.queries.append(query)
        return query

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, _obj):
        return None


def test_get_conversation_filters_tenant_and_conversation_id():
    db = FakeDB()
    repo = ConversationRepository(db, "11111111-1111-1111-1111-111111111111")

    repo.get_conversation(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))

    assert "conversations.tenant_id = :tenant_id_1" in db.queries[0].filters
    assert "conversations.conversation_id = :conversation_id_1" in db.queries[0].filters


def test_list_turns_applies_tenant_scope_and_limit():
    db = FakeDB()
    repo = ConversationRepository(db, "11111111-1111-1111-1111-111111111111")

    repo.list_turns(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"), limit=7)

    assert "conversation_turns.tenant_id = :tenant_id_1" in db.queries[0].filters
    assert "conversation_turns.conversation_id = :conversation_id_1" in db.queries[0].filters
    assert db.queries[0].limit_value == 7


def test_list_retrieval_trace_items_without_turn_filter_avoids_turn_predicate():
    db = FakeDB()
    repo = ConversationRepository(db, "11111111-1111-1111-1111-111111111111")

    repo.list_retrieval_trace_items(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"), turn_id=None)

    filters = db.queries[0].filters
    assert "retrieval_trace_items.tenant_id = :tenant_id_1" in filters
    assert "retrieval_trace_items.conversation_id = :conversation_id_1" in filters
    assert not any("retrieval_trace_items.turn_id" in predicate for predicate in filters)


def test_list_retrieval_trace_items_with_turn_filter_applies_turn_predicate():
    db = FakeDB()
    repo = ConversationRepository(db, "11111111-1111-1111-1111-111111111111")

    repo.list_retrieval_trace_items(
        uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        turn_id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        limit=3,
    )

    filters = db.queries[0].filters
    assert "retrieval_trace_items.tenant_id = :tenant_id_1" in filters
    assert "retrieval_trace_items.conversation_id = :conversation_id_1" in filters
    assert "retrieval_trace_items.turn_id = :turn_id_1" in filters
    assert db.queries[0].limit_value == 3


def test_list_summaries_applies_tenant_scope_and_limit():
    db = FakeDB()
    repo = ConversationRepository(db, "11111111-1111-1111-1111-111111111111")

    repo.list_summaries(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"), limit=5)

    assert "conversation_summaries.tenant_id = :tenant_id_1" in db.queries[0].filters
    assert "conversation_summaries.conversation_id = :conversation_id_1" in db.queries[0].filters
    assert db.queries[0].limit_value == 5


def test_create_conversation_persists_with_tenant_scope():
    db = FakeDB()
    repo = ConversationRepository(db, "11111111-1111-1111-1111-111111111111")

    conversation = repo.create_conversation(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))

    assert conversation.tenant_id == "11111111-1111-1111-1111-111111111111"
    assert conversation.status == "active"
    assert db.commits == 1


def test_get_next_turn_index_returns_first_turn_when_no_turns():
    db = FakeDB(first_results=[None])
    repo = ConversationRepository(db, "11111111-1111-1111-1111-111111111111")

    next_turn = repo.get_next_turn_index(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))

    assert next_turn == 1


def test_get_next_turn_index_increments_existing_turn():
    turn = type("Turn", (), {"turn_index": 4})()
    db = FakeDB(first_results=[turn])
    repo = ConversationRepository(db, "11111111-1111-1111-1111-111111111111")

    next_turn = repo.get_next_turn_index(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))

    assert next_turn == 5


def test_create_turn_without_index_uses_next_index():
    turn = type("Turn", (), {"turn_index": 9})()
    db = FakeDB(first_results=[turn])
    repo = ConversationRepository(db, "11111111-1111-1111-1111-111111111111")

    created_turn = repo.create_turn(
        uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        role="user",
        text="hello",
        meta={"client_turn_id": "1"},
    )

    assert created_turn.turn_index == 10
    assert created_turn.role == "user"
    assert created_turn.meta == {"client_turn_id": "1"}
    assert db.commits == 1


def test_create_query_resolution_persists_rewrite_payload():
    turn = type("Turn", (), {"turn_index": 1})()
    db = FakeDB(first_results=[turn])
    repo = ConversationRepository(db, "11111111-1111-1111-1111-111111111111")

    resolution = repo.create_query_resolution(
        conversation_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        turn_id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        resolved_query_text="resolved",
        rewrite_strategy="llm_rewrite",
        rewrite_inputs={"x": 1},
        rewrite_confidence=0.7,
        topic_shift_detected=False,
        needs_clarification=False,
        clarification_question=None,
    )

    assert resolution.tenant_id == "11111111-1111-1111-1111-111111111111"
    assert resolution.resolved_query_text == "resolved"
    assert resolution.rewrite_strategy == "llm_rewrite"
    assert db.commits == 1


def test_create_retrieval_trace_items_persists_batch():
    db = FakeDB()
    repo = ConversationRepository(db, "11111111-1111-1111-1111-111111111111")

    created = repo.create_retrieval_trace_items(
        [
            {
                "conversation_id": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                "turn_id": uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                "document_id": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
                "chunk_id": uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
                "ordinal": 1,
                "score_lex_raw": 0.1,
                "score_vec_raw": 0.2,
                "score_rerank_raw": 0.3,
                "score_final": 0.4,
                "used_in_context": True,
                "used_in_answer": True,
                "citation_rank": 1,
            }
        ]
    )

    assert created == 1
    assert db.commits == 1


def test_get_latest_query_resolution_filters_tenant_and_conversation():
    db = FakeDB()
    repo = ConversationRepository(db, "11111111-1111-1111-1111-111111111111")

    repo.get_latest_query_resolution(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))

    assert "query_resolutions.tenant_id = :tenant_id_1" in db.queries[0].filters
    assert "query_resolutions.conversation_id = :conversation_id_1" in db.queries[0].filters


def test_count_recent_consecutive_clarifications_stops_on_first_non_clarification():
    rows = [
        type("R", (), {"needs_clarification": True})(),
        type("R", (), {"needs_clarification": True})(),
        type("R", (), {"needs_clarification": False})(),
        type("R", (), {"needs_clarification": True})(),
    ]

    class ClarifyDB(FakeDB):
        def query(self, *_args, **_kwargs):
            q = FakeQuery()
            q.all = lambda: rows
            self.queries.append(q)
            return q

    db = ClarifyDB()
    repo = ConversationRepository(db, "11111111-1111-1111-1111-111111111111")

    count = repo.count_recent_consecutive_clarifications(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))

    assert count == 2


def test_create_summary_increments_version():
    latest = type("S", (), {"summary_version": 2})()

    class SummaryDB(FakeDB):
        def query(self, *_args, **_kwargs):
            q = FakeQuery(first_result=latest)
            self.queries.append(q)
            return q

    db = SummaryDB()
    repo = ConversationRepository(db, "11111111-1111-1111-1111-111111111111")

    summary = repo.create_summary(
        conversation_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        summary_text="summary",
        covers_turn_index_to=12,
    )

    assert summary.summary_version == 3
    assert summary.covers_turn_index_to == 12


def test_get_latest_summary_filters_tenant_and_conversation():
    db = FakeDB()
    repo = ConversationRepository(db, "11111111-1111-1111-1111-111111111111")

    repo.get_latest_summary(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))

    assert "conversation_summaries.tenant_id = :tenant_id_1" in db.queries[0].filters
    assert "conversation_summaries.conversation_id = :conversation_id_1" in db.queries[0].filters
