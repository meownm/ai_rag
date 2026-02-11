from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class BotState(str, Enum):
    IDLE = "IDLE"
    AWAITING_QUESTION = "AWAITING_QUESTION"
    PROCESSING = "PROCESSING"
    CLARIFICATION = "CLARIFICATION"
    ANSWER = "ANSWER"
    ERROR = "ERROR"
    DEBUG = "DEBUG"


@dataclass(slots=True)
class ConversationContext:
    user_id: int
    state: BotState = BotState.IDLE
    conversation_id: str = field(default_factory=lambda: str(uuid4()))
    clarification_depth: int = 0
    last_question: str | None = None
    pending_clarification: list[str] = field(default_factory=list)
    debug_enabled: bool = False
    processing: bool = False
    last_response: dict[str, Any] | None = None


@dataclass(slots=True)
class UiConfig:
    rag_api_url: str
    max_clarification_depth: int = 2
    enable_debug_command: bool = False
    ui_debug_default: bool = False
    admin_user_ids: set[int] = field(default_factory=set)
