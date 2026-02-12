from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from uuid import uuid4

from telegram_ui.fsm import PostgresConversationStore
from telegram_ui.models import BotState, ConversationContext


@dataclass
class _Result:
    rowcount: int = 0

    def mappings(self):
        return self

    def first(self):
        return None


class _MappingResult:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def first(self):
        return self._row


class FakeSession:
    def __init__(self, db: dict[int, dict], lock: Lock) -> None:
        self._db = db
        self._lock = lock
        self._tx_lock: Lock | None = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    @contextmanager
    def begin(self):
        with self._lock:
            yield self

    def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}

        if "DELETE FROM telegram_conversations" in sql:
            ttl_hours = int(params["ttl_hours"])
            threshold = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)
            to_delete = [user_id for user_id, row in self._db.items() if row["updated_at"] < threshold]
            for user_id in to_delete:
                del self._db[user_id]
            return _Result(rowcount=len(to_delete))

        if "INSERT INTO telegram_conversations" in sql:
            user_id = int(params["user_id"])
            self._db[user_id] = {
                "user_id": user_id,
                "conversation_id": str(params["conversation_id"]),
                "state": str(params["state"]),
                "clarification_depth": int(params["clarification_depth"]),
                "debug_enabled": bool(params["debug_enabled"]),
                "last_question": params.get("last_question"),
                "updated_at": datetime.now(timezone.utc),
            }
            return _Result(rowcount=1)

        if "SELECT user_id, conversation_id" in sql:
            row = self._db.get(int(params["user_id"]))
            return _MappingResult(dict(row) if row else None)

        raise AssertionError(f"Unexpected SQL: {sql}")


class FakeSessionFactory:
    def __init__(self) -> None:
        self.db: dict[int, dict] = {}
        self.lock = Lock()

    def __call__(self):
        return FakeSession(self.db, self.lock)


def test_postgres_store_persists_state_and_supports_restart():
    sessions = FakeSessionFactory()
    store = PostgresConversationStore(sessions)

    context = store.get_or_create(42, debug_default=True)
    assert context.debug_enabled is True

    store.upsert(
        user_id=42,
        state=BotState.AWAITING_QUESTION,
        conversation_id=context.conversation_id,
        clarification_depth=1,
        debug_enabled=True,
        last_question="hello",
    )

    restored = PostgresConversationStore(sessions).get(42)
    assert restored is not None
    assert restored.state == BotState.AWAITING_QUESTION
    assert restored.clarification_depth == 1
    assert restored.last_question == "hello"


def test_postgres_store_prevents_concurrent_processing_race():
    sessions = FakeSessionFactory()
    store = PostgresConversationStore(sessions)
    store.get_or_create(7)

    def begin_once() -> bool:
        return store.try_begin_processing(7)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = list(executor.map(lambda _: begin_once(), [0, 1]))

    assert sorted([first, second]) == [False, True]


def test_postgres_store_reset_clears_state_and_depth():
    sessions = FakeSessionFactory()
    store = PostgresConversationStore(sessions)

    conversation_id = str(uuid4())
    store.upsert(
        user_id=9,
        state=BotState.CLARIFICATION,
        conversation_id=conversation_id,
        clarification_depth=2,
        debug_enabled=True,
        last_question="q",
    )

    reset = store.reset(9)
    assert reset.state == BotState.AWAITING_QUESTION
    assert reset.clarification_depth == 0
    assert reset.last_question is None
    assert reset.conversation_id != conversation_id


def test_cleanup_deletes_expired_rows_and_respects_interval():
    sessions = FakeSessionFactory()
    store = PostgresConversationStore(sessions, ttl_hours=1, cleanup_interval_seconds=3600)
    created = store.get_or_create(11)
    sessions.db[11]["updated_at"] = datetime.now(timezone.utc) - timedelta(hours=5)

    deleted = store.run_cleanup(force=True)
    assert deleted == 1
    assert store.get(11) is None

    store.get_or_create(11)
    sessions.db[11]["updated_at"] = datetime.now(timezone.utc) - timedelta(hours=5)
    skipped = store.maybe_run_cleanup()
    assert skipped == 0
