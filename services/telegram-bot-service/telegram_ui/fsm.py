from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from threading import Lock
from uuid import UUID, uuid4

from .models import BotState, ConversationContext


class InvalidTransitionError(ValueError):
    pass


class ConcurrentProcessingError(RuntimeError):
    pass


class PostgresConversationStore:
    def __init__(
        self,
        session_factory,
        *,
        ttl_hours: int = 24,
        cleanup_interval_seconds: int = 1800,
        logger: logging.Logger | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._ttl_hours = ttl_hours
        self._cleanup_interval_seconds = cleanup_interval_seconds
        self._logger = logger or logging.getLogger(__name__)
        self._cleanup_lock = Lock()
        self._last_cleanup_ts: datetime | None = None

    @staticmethod
    def _row_to_context(row: dict) -> ConversationContext:
        return ConversationContext(
            user_id=int(row["user_id"]),
            state=BotState(row["state"]),
            conversation_id=str(row["conversation_id"]),
            clarification_depth=int(row["clarification_depth"]),
            last_question=row.get("last_question"),
            debug_enabled=bool(row["debug_enabled"]),
            processing=BotState(row["state"]) == BotState.PROCESSING,
        )

    def get(self, user_id: int) -> ConversationContext | None:
        with self._session_factory() as session:
            row = (
                session.execute(
                    """
                    SELECT user_id, conversation_id, state, clarification_depth, debug_enabled, last_question
                    FROM telegram_conversations
                    WHERE user_id = :user_id
                    """,
                    {"user_id": user_id},
                )
                .mappings()
                .first()
            )
            if row is None:
                return None
            return self._row_to_context(row)

    def get_or_create(self, user_id: int, debug_default: bool = False) -> ConversationContext:
        existing = self.get(user_id)
        if existing is not None:
            return existing
        context = ConversationContext(user_id=user_id, debug_enabled=debug_default)
        self.upsert(
            user_id=user_id,
            state=context.state,
            conversation_id=context.conversation_id,
            clarification_depth=context.clarification_depth,
            debug_enabled=context.debug_enabled,
            last_question=context.last_question,
        )
        return context

    def upsert(
        self,
        user_id: int,
        state: BotState,
        conversation_id: str,
        clarification_depth: int,
        debug_enabled: bool,
        last_question: str | None,
    ) -> None:
        with self._session_factory() as session:
            with session.begin():
                session.execute(
                    """
                    INSERT INTO telegram_conversations (
                        user_id,
                        conversation_id,
                        state,
                        clarification_depth,
                        debug_enabled,
                        last_question,
                        updated_at
                    ) VALUES (
                        :user_id,
                        :conversation_id,
                        :state,
                        :clarification_depth,
                        :debug_enabled,
                        :last_question,
                        now()
                    )
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        conversation_id = EXCLUDED.conversation_id,
                        state = EXCLUDED.state,
                        clarification_depth = EXCLUDED.clarification_depth,
                        debug_enabled = EXCLUDED.debug_enabled,
                        last_question = EXCLUDED.last_question,
                        updated_at = now()
                    """,
                    {
                        "user_id": user_id,
                        "conversation_id": str(UUID(conversation_id)),
                        "state": state.value,
                        "clarification_depth": clarification_depth,
                        "debug_enabled": debug_enabled,
                        "last_question": last_question,
                    },
                )

    def update(self, user_id: int, updater: Callable[[ConversationContext], None]) -> ConversationContext:
        with self._session_factory() as session:
            with session.begin():
                context = self._load_for_update(session, user_id)
                updater(context)
                self._upsert_context(session, context)
                return context

    def reset(self, user_id: int) -> ConversationContext:
        with self._session_factory() as session:
            with session.begin():
                context = self._load_for_update(session, user_id)
                context.conversation_id = str(uuid4())
                context.clarification_depth = 0
                context.last_question = None
                context.state = BotState.AWAITING_QUESTION
                self._upsert_context(session, context)
                return context

    def reset_dialog(self, user_id: int) -> ConversationContext:
        return self.reset(user_id)

    def try_begin_processing(self, user_id: int) -> bool:
        with self._session_factory() as session:
            with session.begin():
                context = self._load_for_update(session, user_id)
                if context.state == BotState.PROCESSING:
                    return False
                context.state = BotState.PROCESSING
                self._upsert_context(session, context)
                return True

    def finish_processing(self, user_id: int) -> None:
        with self._session_factory() as session:
            with session.begin():
                context = self._load_for_update(session, user_id)
                # processing flag is represented by PROCESSING state and is updated by normal transitions
                self._upsert_context(session, context)

    def run_cleanup(self, *, force: bool = False) -> int:
        with self._cleanup_lock:
            now_ts = datetime.now(timezone.utc)
            if not force and self._last_cleanup_ts is not None:
                elapsed = (now_ts - self._last_cleanup_ts).total_seconds()
                if elapsed < self._cleanup_interval_seconds:
                    return 0
            deleted_rows = self._delete_expired_rows()
            self._last_cleanup_ts = now_ts
            self._logger.info(
                "fsm_cleanup",
                extra={
                    "event": "fsm_cleanup",
                    "deleted_rows": deleted_rows,
                    "ttl_hours": self._ttl_hours,
                },
            )
            return deleted_rows

    def maybe_run_cleanup(self) -> int:
        return self.run_cleanup(force=False)

    def _delete_expired_rows(self) -> int:
        with self._session_factory() as session:
            with session.begin():
                result = session.execute(
                    """
                    DELETE FROM telegram_conversations
                    WHERE updated_at < now() - make_interval(hours => :ttl_hours)
                    """,
                    {"ttl_hours": int(self._ttl_hours)},
                )
                return int(result.rowcount or 0)

    def _load_for_update(self, session, user_id: int) -> ConversationContext:
        row = (
            session.execute(
                """
                SELECT user_id, conversation_id, state, clarification_depth, debug_enabled, last_question
                FROM telegram_conversations
                WHERE user_id = :user_id
                FOR UPDATE
                """,
                {"user_id": user_id},
            )
            .mappings()
            .first()
        )
        if row is None:
            return ConversationContext(user_id=user_id)
        return self._row_to_context(row)

    def _upsert_context(self, session, context: ConversationContext) -> None:
        session.execute(
            """
            INSERT INTO telegram_conversations (
                user_id,
                conversation_id,
                state,
                clarification_depth,
                debug_enabled,
                last_question,
                updated_at
            ) VALUES (
                :user_id,
                :conversation_id,
                :state,
                :clarification_depth,
                :debug_enabled,
                :last_question,
                now()
            )
            ON CONFLICT (user_id)
            DO UPDATE SET
                conversation_id = EXCLUDED.conversation_id,
                state = EXCLUDED.state,
                clarification_depth = EXCLUDED.clarification_depth,
                debug_enabled = EXCLUDED.debug_enabled,
                last_question = EXCLUDED.last_question,
                updated_at = now()
            """,
            {
                "user_id": context.user_id,
                "conversation_id": str(UUID(context.conversation_id)),
                "state": context.state.value,
                "clarification_depth": context.clarification_depth,
                "debug_enabled": context.debug_enabled,
                "last_question": context.last_question,
            },
        )


ALLOWED_TRANSITIONS: dict[BotState, set[BotState]] = {
    BotState.IDLE: {BotState.AWAITING_QUESTION},
    BotState.AWAITING_QUESTION: {BotState.PROCESSING},
    BotState.PROCESSING: {BotState.CLARIFICATION, BotState.ANSWER, BotState.ERROR},
    BotState.CLARIFICATION: {BotState.PROCESSING, BotState.AWAITING_QUESTION},
    BotState.ANSWER: {BotState.PROCESSING, BotState.AWAITING_QUESTION, BotState.DEBUG},
    BotState.DEBUG: {BotState.ANSWER},
    BotState.ERROR: {BotState.AWAITING_QUESTION},
}


def transition(context: ConversationContext, next_state: BotState) -> None:
    if next_state not in ALLOWED_TRANSITIONS.get(context.state, set()):
        raise InvalidTransitionError(f"Invalid transition: {context.state} -> {next_state}")
    context.state = next_state
