from __future__ import annotations

from collections.abc import Callable
from threading import Lock

from .models import BotState, ConversationContext


class InvalidTransitionError(ValueError):
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
