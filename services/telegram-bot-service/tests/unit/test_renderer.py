from telegram_ui.models import ConversationContext
from telegram_ui.renderer import MAX_MESSAGE_SIZE, assistant_messages


def test_structured_answer_contains_summary_details_sources():
    context = ConversationContext(user_id=1)
    out = assistant_messages(
        answer="Кратко",
        details="Подробно",
        sources=["Doc A", "Doc B"],
        context=context,
    )

    text = out[0].text
    assert "📌 Кратко" in text
    assert "🧠 Детали" in text
    assert "📚 Источники" in text
    assert "Doc A" in text


def test_long_response_split_is_safe_and_keyboard_only_on_first_chunk():
    context = ConversationContext(user_id=1)
    huge = "A" * (MAX_MESSAGE_SIZE + 200)

    out = assistant_messages(
        answer=huge,
        details="details",
        sources=["src"],
        context=context,
    )

    assert len(out) >= 2
    assert out[0].inline_keyboard is not None
    assert all(item.inline_keyboard is None for item in out[1:])
    assert all(len(item.text) <= MAX_MESSAGE_SIZE for item in out)
