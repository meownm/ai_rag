from __future__ import annotations

from dataclasses import dataclass

from .models import ConversationContext

MAX_MESSAGE_SIZE = 3500


@dataclass(slots=True)
class OutboundMessage:
    text: str
    inline_keyboard: list[list[dict[str, str]]] | None = None


def _split_chunks(text: str, max_len: int = MAX_MESSAGE_SIZE) -> list[str]:
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current = ""

    def flush_current() -> None:
        nonlocal current
        if current:
            chunks.append(current)
            current = ""

    for paragraph in text.split("\n"):
        if not paragraph:
            candidate = f"{current}\n" if current else ""
            if len(candidate) <= max_len:
                current = candidate
            else:
                flush_current()
            continue

        while len(paragraph) > max_len:
            piece = paragraph[:max_len]
            paragraph = paragraph[max_len:]
            flush_current()
            chunks.append(piece)

        candidate = f"{current}\n{paragraph}" if current else paragraph
        if len(candidate) <= max_len:
            current = candidate
        else:
            flush_current()
            current = paragraph

    flush_current()
    return chunks


def assistant_messages(answer: str, details: str, sources: list[str], context: ConversationContext, debug_block: str | None = None) -> list[OutboundMessage]:
    source_text = "\n".join(f"• {source}" for source in sources) if sources else "• Источники не найдены"
    structured = f"📌 Кратко\n{answer}\n\n🧠 Детали\n{details}\n\n📚 Источники\n{source_text}"
    if debug_block and context.debug_enabled:
        structured = f"{structured}\n\n🔍 Debug\n{debug_block}"

    keyboard = [
        [{"text": "🔁 Уточнить", "callback_data": "clarify"}, {"text": "📚 Похожие темы", "callback_data": "similar_topics"}],
        [{"text": "🆕 Новый диалог", "callback_data": "new_dialog"}, {"text": "ℹ️ Детали анализа", "callback_data": "analysis_details"}],
    ]
    chunks = _split_chunks(structured)
    messages: list[OutboundMessage] = []
    for idx, chunk in enumerate(chunks):
        messages.append(OutboundMessage(text=chunk, inline_keyboard=keyboard if idx == 0 else None))
    return messages


def clarification_keyboard(options: list[str]) -> list[list[dict[str, str]]]:
    rows = [[{"text": option, "callback_data": f"clarification:{index}"}] for index, option in enumerate(options)]
    rows.append([{"text": "Отмена", "callback_data": "clarification:cancel"}])
    return rows
