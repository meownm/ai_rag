"""Manages conversation lifecycle, history, summarization and topic detection."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.math_utils import cosine_similarity
from app.core.token_utils import estimate_tokens
from app.db.repositories import ConversationRepository
from app.models.models import Conversations, ConversationTurns


@dataclass
class TopicResetResult:
    should_reset: bool
    similarity: float


@dataclass
class ConversationContext:
    """All conversation-related state needed by the query pipeline."""
    conversation_id: uuid.UUID
    conversation_repo: ConversationRepository
    user_turn: ConversationTurns
    history_turns: list[dict]
    summary_text: str | None
    topic_reset: TopicResetResult | None
    clarification_pending: bool
    last_clarification_question: str | None


class ConversationManager:
    """Encapsulates conversation lifecycle and history management."""

    def __init__(self, db: Session, tenant_id: str | uuid.UUID):
        self.repo = ConversationRepository(db, tenant_id)
        self.tenant_id = str(tenant_id)

    def ensure_conversation(self, conversation_id: uuid.UUID) -> Conversations:
        conversation = self.repo.get_conversation(conversation_id)
        if conversation is None:
            return self.repo.create_conversation(conversation_id)
        ttl_cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.CONVERSATION_TTL_MINUTES)
        last_active_at = conversation.last_active_at
        if last_active_at is not None and last_active_at.tzinfo is None:
            last_active_at = last_active_at.replace(tzinfo=timezone.utc)
        if last_active_at and last_active_at < ttl_cutoff:
            self.repo.mark_conversation_archived(conversation)
        self.repo.touch_conversation(conversation)
        return conversation

    def record_user_turn(
        self,
        conversation_id: uuid.UUID,
        text: str,
        *,
        client_turn_id: str | None = None,
    ) -> ConversationTurns:
        meta = {}
        if client_turn_id:
            meta["client_turn_id"] = client_turn_id
        return self.repo.create_turn(conversation_id, "user", text, meta=meta or None)

    def record_assistant_turn(
        self,
        conversation_id: uuid.UUID,
        text: str,
        *,
        correlation_id: str | None = None,
        extra_meta: dict | None = None,
    ) -> ConversationTurns:
        meta = {}
        if correlation_id:
            meta["correlation_id"] = correlation_id
        if extra_meta:
            meta.update(extra_meta)
        return self.repo.create_turn(conversation_id, "assistant", text, meta=meta or None)

    def maybe_summarize(self, conversation_id: uuid.UUID, summarizer) -> None:
        """Create a conversation summary if the turn count exceeds the threshold."""
        recent_turns = [
            {"role": t.role, "text": t.text, "turn_index": int(t.turn_index)}
            for t in reversed(
                self.repo.list_turns(
                    conversation_id,
                    limit=max(settings.CONVERSATION_SUMMARY_THRESHOLD_TURNS + 5, 20),
                )
            )
        ]
        if len(recent_turns) < settings.CONVERSATION_SUMMARY_THRESHOLD_TURNS:
            return

        latest_summary = self.repo.get_latest_summary(conversation_id)
        max_turn_index = max((int(t.get("turn_index", 0)) for t in recent_turns), default=0)
        covered_index = int(latest_summary.covers_turn_index_to) if latest_summary is not None else 0

        if max_turn_index <= covered_index:
            return

        masked_mode = settings.LOG_DATA_MODE.strip().lower() == "masked"
        summary_text = summarizer.summarize(recent_turns, masked_mode=masked_mode)
        self.repo.create_summary(
            conversation_id=conversation_id,
            summary_text=summary_text,
            covers_turn_index_to=max_turn_index,
        )

    def get_history_for_rewrite(
        self,
        conversation_id: uuid.UUID,
    ) -> tuple[list[dict], str | None]:
        """Return trimmed history turns and latest summary text."""
        base_turns = [
            {"role": t.role, "text": t.text}
            for t in reversed(
                self.repo.list_turns(
                    conversation_id,
                    limit=max(settings.CONVERSATION_TURNS_LAST_N, settings.MAX_HISTORY_TURNS + 2),
                )
            )
        ]
        trimmed = self._trim_history_turns(base_turns)
        latest_summary = self.repo.get_latest_summary(conversation_id)
        summary_text = latest_summary.summary_text if latest_summary else None
        return trimmed, summary_text

    def get_previous_user_query(self, conversation_id: uuid.UUID) -> str:
        """Return the text of the previous user turn (if any)."""
        base_turns = [
            {"role": t.role, "text": t.text}
            for t in reversed(
                self.repo.list_turns(
                    conversation_id,
                    limit=max(settings.CONVERSATION_TURNS_LAST_N, settings.MAX_HISTORY_TURNS + 2),
                )
            )
        ]
        # Skip the current (last) turn to get previous user query
        return next(
            (str(t.get("text", "")) for t in reversed(base_turns[:-1]) if str(t.get("role", "")).lower() == "user"),
            "",
        )

    def check_clarification_state(self, conversation_id: uuid.UUID) -> tuple[bool, str | None]:
        """Return (clarification_pending, last_clarification_question)."""
        latest_resolution = self.repo.get_latest_query_resolution(conversation_id)
        if latest_resolution is not None and bool(latest_resolution.needs_clarification):
            return True, latest_resolution.clarification_question
        return False, None

    @staticmethod
    def detect_topic_reset(
        current_embedding: list[float],
        previous_embedding: list[float],
        threshold: float | None = None,
    ) -> TopicResetResult:
        threshold = threshold if threshold is not None else settings.TOPIC_RESET_SIMILARITY_THRESHOLD
        similarity = cosine_similarity(current_embedding, previous_embedding)
        should_reset = bool(settings.TOPIC_RESET_ENABLED) and similarity < float(threshold)
        return TopicResetResult(should_reset=should_reset, similarity=similarity)

    @staticmethod
    def _trim_history_turns(turns: list[dict]) -> list[dict]:
        limited = list(turns[-settings.MAX_HISTORY_TURNS:])
        trimmed: list[dict] = []
        token_sum = 0
        for turn in reversed(limited):
            turn_tokens = estimate_tokens(str(turn.get("text", "")))
            if token_sum + turn_tokens > settings.MAX_HISTORY_TOKENS:
                continue
            trimmed.append(turn)
            token_sum += turn_tokens
        return list(reversed(trimmed))

    def apply_memory_boosting(
        self,
        candidates: list[dict],
        conversation_id: uuid.UUID,
        max_boost: float = 0.12,
    ) -> tuple[list[dict], int]:
        """Boost candidates that appeared in recent answers."""
        previous_trace = self.repo.list_retrieval_trace_items(conversation_id, limit=50)
        return self._boost_from_trace(candidates, previous_trace, max_boost)

    @staticmethod
    def _boost_from_trace(
        candidates: list[dict],
        previous_trace_items: list[object],
        max_boost: float = 0.12,
    ) -> tuple[list[dict], int]:
        boosts_by_key: dict[tuple[str, str], float] = {}
        for rank, item in enumerate(previous_trace_items[:20]):
            try:
                if not bool(getattr(item, "used_in_answer", False)):
                    continue
                doc_id = str(getattr(item, "document_id"))
                chunk_id = str(getattr(item, "chunk_id"))
                recency = max(0.3, 1.0 - (rank * 0.2))
                boosts_by_key[(doc_id, chunk_id)] = max(
                    boosts_by_key.get((doc_id, chunk_id), 0.0),
                    max_boost * recency,
                )
            except Exception:  # noqa: BLE001
                continue

        boosted = 0
        updated = []
        for entry in candidates:
            doc_id = str(entry.get("document_id"))
            chunk_id = str(entry.get("chunk_id"))
            boost = min(max_boost, boosts_by_key.get((doc_id, chunk_id), 0.0))
            if boost > 0:
                entry["final_score"] = float(entry.get("final_score", 0.0)) + boost
                entry.setdefault("boosts_applied", []).append(
                    {"name": "memory_reuse_boost", "value": boost, "reason": "recent_answer_reuse"}
                )
                boosted += 1
            updated.append(entry)

        updated.sort(key=lambda x: (-float(x.get("final_score", 0.0)), str(x.get("chunk_id"))))
        return updated, boosted

    @staticmethod
    def build_retrieval_trace_rows(
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
        ranked_candidates: list[dict],
        chosen_candidates: list[dict],
    ) -> list[dict]:
        chosen_ids = {str(c.get("chunk_id")) for c in chosen_candidates}
        citation_ranks = {str(c.get("chunk_id")): idx + 1 for idx, c in enumerate(chosen_candidates)}
        rows: list[dict] = []
        for idx, candidate in enumerate(ranked_candidates, start=1):
            doc_id = _safe_uuid(candidate.get("document_id"))
            chunk_id = _safe_uuid(candidate.get("chunk_id"))
            if doc_id is None or chunk_id is None:
                continue
            candidate_id = str(candidate.get("chunk_id"))
            rows.append(
                {
                    "conversation_id": conversation_id,
                    "turn_id": turn_id,
                    "document_id": doc_id,
                    "chunk_id": chunk_id,
                    "ordinal": idx,
                    "score_lex_raw": float(candidate.get("lex_raw", candidate.get("lex_score", 0.0))),
                    "score_vec_raw": float(candidate.get("vec_raw", candidate.get("vec_score", 0.0))),
                    "score_rerank_raw": float(candidate.get("rerank_raw", candidate.get("rerank_score", 0.0))),
                    "score_final": float(candidate.get("final_score", 0.0)),
                    "used_in_context": candidate_id in chosen_ids,
                    "used_in_answer": candidate_id in chosen_ids,
                    "citation_rank": citation_ranks.get(candidate_id),
                }
            )
        return rows


def _safe_uuid(value: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None
