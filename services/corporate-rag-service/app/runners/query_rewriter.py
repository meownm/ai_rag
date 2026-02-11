from __future__ import annotations

import json
from dataclasses import dataclass

from app.clients.ollama_client import OllamaClient
from app.core.config import settings

QUERY_REWRITE_JSON_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "resolved_query_text",
        "follow_up",
        "topic_shift",
        "intent",
        "entities",
        "clarification_needed",
        "clarification_question",
        "confidence",
    ],
    "properties": {
        "resolved_query_text": {"type": "string", "minLength": 1},
        "follow_up": {"type": "boolean"},
        "topic_shift": {"type": "boolean"},
        "intent": {"type": "string"},
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["type", "value"],
                "properties": {
                    "type": {"type": "string"},
                    "value": {"type": "string"},
                },
            },
        },
        "clarification_needed": {"type": "boolean"},
        "clarification_question": {"type": ["string", "null"]},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
}


@dataclass(frozen=True)
class QueryRewriteResult:
    resolved_query_text: str
    follow_up: bool
    topic_shift: bool
    intent: str
    entities: list[dict[str, str]]
    clarification_needed: bool
    clarification_question: str | None
    confidence: float


class QueryRewriteError(RuntimeError):
    pass


def _build_rewrite_prompt(
    user_query: str,
    summary: str | None,
    recent_turns: list[dict],
    citation_hints: list[dict] | None,
    clarification_pending: bool = False,
    last_question: str | None = None,
) -> str:
    turns_text = "\n".join(
        [f"- {t.get('role', 'unknown')}: {t.get('text', '').strip()}" for t in recent_turns if str(t.get("text", "")).strip()]
    )
    hints_text = "\n".join(
        [
            f"- source={h.get('source', '')}; title={h.get('title', '')}; chunk_ordinal={h.get('chunk_ordinal', '')}"
            for h in (citation_hints or [])
        ]
    )
    prompt_summary = summary or ""
    clarification_block = ""
    if clarification_pending and last_question:
        clarification_block = f"ClarificationPending: true\nLastClarificationQuestion:\n{last_question}\n\n"

    return (
        "You are a query rewriting module for enterprise RAG.\n"
        "Return one JSON object only, with no prose or markdown.\n"
        "Rewrite the latest user query so retrieval can run safely.\n\n"
        f"ConversationSummary:\n{prompt_summary}\n\n"
        f"RecentTurns:\n{turns_text or '- (none)'}\n\n"
        f"CitationHints:\n{hints_text or '- (none)'}\n\n"
        f"{clarification_block}"
        f"LatestUserQuery:\n{user_query}\n\n"
        "JSON output contract:\n"
        '{"resolved_query_text":"...","follow_up":true,"topic_shift":false,"intent":"...","entities":[{"type":"...","value":"..."}],"clarification_needed":false,"clarification_question":null,"confidence":0.0}'
    )


def _extract_json(raw: object) -> dict:
    if isinstance(raw, dict):
        if isinstance(raw.get("response"), str):
            return json.loads(raw["response"])
        return raw
    if isinstance(raw, str):
        return json.loads(raw)
    raise QueryRewriteError("Unsupported rewrite response payload")


def _validate_against_schema(payload: dict) -> None:
    required = QUERY_REWRITE_JSON_SCHEMA["required"]
    for field in required:
        if field not in payload:
            raise QueryRewriteError(f"JSON schema validation failed: missing '{field}'")

    if not isinstance(payload["resolved_query_text"], str) or not payload["resolved_query_text"].strip():
        raise QueryRewriteError("JSON schema validation failed: resolved_query_text")
    if not isinstance(payload["follow_up"], bool):
        raise QueryRewriteError("JSON schema validation failed: follow_up")
    if not isinstance(payload["topic_shift"], bool):
        raise QueryRewriteError("JSON schema validation failed: topic_shift")
    if not isinstance(payload["intent"], str):
        raise QueryRewriteError("JSON schema validation failed: intent")
    if not isinstance(payload["clarification_needed"], bool):
        raise QueryRewriteError("JSON schema validation failed: clarification_needed")
    if payload["clarification_question"] is not None and not isinstance(payload["clarification_question"], str):
        raise QueryRewriteError("JSON schema validation failed: clarification_question")

    confidence = payload["confidence"]
    if not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
        raise QueryRewriteError("JSON schema validation failed: confidence")

    entities = payload["entities"]
    if not isinstance(entities, list):
        raise QueryRewriteError("JSON schema validation failed: entities")
    for entity in entities:
        if not isinstance(entity, dict):
            raise QueryRewriteError("JSON schema validation failed: entity type")
        if set(entity.keys()) != {"type", "value"}:
            raise QueryRewriteError("JSON schema validation failed: entity keys")
        if not isinstance(entity["type"], str) or not isinstance(entity["value"], str):
            raise QueryRewriteError("JSON schema validation failed: entity values")


class QueryRewriter:
    def __init__(self, model_id: str | None = None, keep_alive: int | None = None):
        self.model_id = model_id or settings.REWRITE_MODEL_ID
        self.keep_alive = settings.REWRITE_KEEP_ALIVE if keep_alive is None else int(keep_alive)

    def rewrite(
        self,
        *,
        tenant_id: str,
        conversation_id: str | None,
        user_query: str,
        recent_turns: list[dict],
        summary: str | None = None,
        citation_hints: list[dict] | None = None,
        clarification_pending: bool = False,
        last_question: str | None = None,
    ) -> QueryRewriteResult:
        _ = tenant_id
        _ = conversation_id

        prompt = _build_rewrite_prompt(
            user_query,
            summary,
            recent_turns,
            citation_hints,
            clarification_pending=clarification_pending,
            last_question=last_question,
        )
        client = OllamaClient(settings.LLM_ENDPOINT, self.model_id, settings.REQUEST_TIMEOUT_SECONDS)
        payload = client.generate(prompt, keep_alive=self.keep_alive)

        parsed = _extract_json(payload)
        _validate_against_schema(parsed)

        return QueryRewriteResult(
            resolved_query_text=str(parsed["resolved_query_text"]),
            follow_up=bool(parsed["follow_up"]),
            topic_shift=bool(parsed["topic_shift"]),
            intent=str(parsed["intent"]),
            entities=[{"type": str(e["type"]), "value": str(e["value"])} for e in parsed["entities"]],
            clarification_needed=bool(parsed["clarification_needed"]),
            clarification_question=parsed["clarification_question"],
            confidence=float(parsed["confidence"]),
        )
