from __future__ import annotations

from app.clients.ollama_client import OllamaClient
from app.core.config import settings


class ConversationSummarizer:
    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or settings.REWRITE_MODEL_ID

    def summarize(self, recent_turns: list[dict], masked_mode: bool = False) -> str:
        if not recent_turns:
            return "No conversation context yet."

        if masked_mode:
            topics = []
            for turn in recent_turns:
                role = str(turn.get("role", "unknown"))
                text = str(turn.get("text", "")).strip().lower()
                if not text:
                    continue
                topics.append(f"{role}:topic")
            compact_topics = ", ".join(topics[:6]) if topics else "general"
            return f"High-level summary (masked): {compact_topics}."

        turns_text = "\n".join([f"- {t.get('role','unknown')}: {str(t.get('text','')).strip()[:240]}" for t in recent_turns if str(t.get("text", "")).strip()])
        prompt = (
            "Summarize the conversation context for downstream query rewriting. "
            "Keep it short (<= 120 words), factual, and focused on stable user intent, entities, constraints, and open questions. "
            "Return plain text only.\n\n"
            f"Turns:\n{turns_text}"
        )

        client = OllamaClient(settings.LLM_ENDPOINT, self.model_id, settings.REQUEST_TIMEOUT_SECONDS)
        payload = client.generate(prompt, keep_alive=0)
        response = payload.get("response") if isinstance(payload, dict) else str(payload)
        summary = str(response or "").strip()
        if not summary:
            return "Conversation summary unavailable."
        words = summary.split()
        if len(words) > 120:
            summary = " ".join(words[:120])
        return summary
