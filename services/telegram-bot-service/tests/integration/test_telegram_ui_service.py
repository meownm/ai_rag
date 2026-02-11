from telegram_ui.fsm import InMemoryConversationStore
from telegram_ui.models import UiConfig
from telegram_ui.service import TelegramUiService


class FakeRagClient:
    def __init__(self, response):
        self.response = response

    def query(self, question: str, conversation_id: str):
        return self.response(question, conversation_id) if callable(self.response) else self.response


def _service(response, enable_debug: bool = False):
    config = UiConfig(
        rag_api_url="http://localhost:8000",
        max_clarification_depth=2,
        enable_debug_command=enable_debug,
        admin_user_ids={99},
    )
    return TelegramUiService(config=config, rag_client=FakeRagClient(response), store=InMemoryConversationStore())


def test_start_and_successful_response_includes_actions():
    service = _service(
        {
            "summary": "Краткий ответ",
            "details": "Детальный ответ",
            "sources": ["Doc A"],
            "confidence": 0.9,
        }
    )
    start = service.handle_command(1, "/start")
    assert "Задайте вопрос" in start[0].text

    result = service.handle_text(1, "Что в политике отпуска?")
    assert any("📚 Источники" in item.text for item in result)
    assert result[0].inline_keyboard is not None


def test_clarification_flow_button_driven():
    service = _service({"needs_clarification": True, "clarification_options": ["Вариант 1", "Вариант 2"]})
    service.handle_command(1, "/start")
    clarification = service.handle_text(1, "Вопрос")
    assert clarification[0].inline_keyboard is not None
    assert clarification[0].inline_keyboard[0][0]["callback_data"] == "clarification:0"


def test_clarification_depth_limit_goes_to_error():
    service = _service({"needs_clarification": True, "clarification_options": ["Вариант 1"]})
    service.handle_command(1, "/start")
    service.handle_text(1, "1")
    service.handle_callback(1, "clarification:0")
    last = service.handle_callback(1, "clarification:0")
    assert "Не удалось уточнить" in last[0].text


def test_low_confidence_maps_to_friendly_error_without_trace():
    service = _service({"summary": "x", "details": "y", "sources": [], "confidence": 0.1})
    service.handle_command(1, "/start")
    result = service.handle_text(1, "question")
    assert "Недостаточно уверенности" in result[0].text
    assert "Traceback" not in result[0].text


def test_debug_command_admin_only():
    service = _service({"summary": "ok", "details": "d", "sources": [], "confidence": 0.9}, enable_debug=True)
    denied = service.handle_command(1, "/debug")
    assert "недоступна" in denied[0].text

    allowed = service.handle_command(99, "/debug")
    assert "включен" in allowed[0].text
