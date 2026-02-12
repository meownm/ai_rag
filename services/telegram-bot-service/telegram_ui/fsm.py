from __future__ import annotations

import json
from collections.abc import Callable
from threading import Lock

from .models import BotState, ConversationContext


class InvalidTransitionError(ValueError):
    pass


class ConcurrentProcessingError(RuntimeError):
    pass


class InMemoryConversationStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._contexts: dict[int, ConversationContext] = {}

    def get_or_create(self, user_id: int, debug_default: bool = False) -> ConversationContext:
        with self._lock:
            if user_id not in self._contexts:
                self._contexts[user_id] = ConversationContext(user_id=user_id, debug_enabled=debug_default)
            return self._contexts[user_id]

    def update(self, user_id: int, updater: Callable[[ConversationContext], None]) -> ConversationContext:
        with self._lock:
            context = self._contexts[user_id]
            updater(context)
            return context

    def reset_dialog(self, user_id: int) -> ConversationContext:
        with self._lock:
            context = self._contexts[user_id]
            context.conversation_id = ConversationContext(user_id=user_id).conversation_id
            context.clarification_depth = 0
            context.pending_clarification = []
            context.last_question = None
            context.last_response = None
            context.processing = False
            context.state = BotState.AWAITING_QUESTION
            return context

    def try_begin_processing(self, user_id: int) -> bool:
        with self._lock:
            context = self._contexts[user_id]
            if context.processing:
                return False
            context.processing = True
            return True

    def finish_processing(self, user_id: int) -> None:
        with self._lock:
            context = self._contexts[user_id]
            context.processing = False


class RedisConversationStore:
    def __init__(self, redis_client, ttl_seconds: int = 3600) -> None:
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _key(user_id: int) -> str:
        return f"tg:ctx:{user_id}"

    @staticmethod
    def _serialize(context: ConversationContext) -> str:
        payload = {
            "user_id": context.user_id,
            "state": context.state.value,
            "conversation_id": context.conversation_id,
            "clarification_depth": context.clarification_depth,
            "last_question": context.last_question,
            "pending_clarification": context.pending_clarification,
            "debug_enabled": context.debug_enabled,
            "processing": context.processing,
            "last_response": context.last_response,
        }
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _deserialize(raw: str) -> ConversationContext:
        payload = json.loads(raw)
        return ConversationContext(
            user_id=int(payload["user_id"]),
            state=BotState(payload.get("state", BotState.IDLE.value)),
            conversation_id=str(payload.get("conversation_id")),
            clarification_depth=int(payload.get("clarification_depth", 0)),
            last_question=payload.get("last_question"),
            pending_clarification=list(payload.get("pending_clarification", [])),
            debug_enabled=bool(payload.get("debug_enabled", False)),
            processing=bool(payload.get("processing", False)),
            last_response=payload.get("last_response"),
        )

    def _persist(self, context: ConversationContext) -> None:
        self.redis.set(self._key(context.user_id), self._serialize(context), ex=self.ttl_seconds)

    def get_or_create(self, user_id: int, debug_default: bool = False) -> ConversationContext:
        raw = self.redis.get(self._key(user_id))
        if raw:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return self._deserialize(raw)
        context = ConversationContext(user_id=user_id, debug_enabled=debug_default)
        self._persist(context)
        return context

    def update(self, user_id: int, updater: Callable[[ConversationContext], None]) -> ConversationContext:
        context = self.get_or_create(user_id)
        updater(context)
        self._persist(context)
        return context

    def reset_dialog(self, user_id: int) -> ConversationContext:
        context = self.get_or_create(user_id)
        context.conversation_id = ConversationContext(user_id=user_id).conversation_id
        context.clarification_depth = 0
        context.pending_clarification = []
        context.last_question = None
        context.last_response = None
        context.processing = False
        context.state = BotState.AWAITING_QUESTION
        self._persist(context)
        return context

    def try_begin_processing(self, user_id: int) -> bool:
        context = self.get_or_create(user_id)
        if context.processing:
            return False
        context.processing = True
        self._persist(context)
        return True

    def finish_processing(self, user_id: int) -> None:
        context = self.get_or_create(user_id)
        context.processing = False
        self._persist(context)


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
