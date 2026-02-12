import asyncio

from telegram_ui.models import BotState, UiConfig
from telegram_ui.models import ConversationContext


class ConversationStoreStub:
    def __init__(self):
        self._contexts: dict[int, ConversationContext] = {}

    def get_or_create(self, user_id: int, debug_default: bool = False):
        if user_id not in self._contexts:
            self._contexts[user_id] = ConversationContext(user_id=user_id, debug_enabled=debug_default)
        return self._contexts[user_id]

    def update(self, user_id: int, updater):
        context = self._contexts[user_id]
        updater(context)
        return context

    def reset_dialog(self, user_id: int):
        context = self.get_or_create(user_id)
        context.conversation_id = ConversationContext(user_id=user_id).conversation_id
        context.clarification_depth = 0
        context.pending_clarification = []
        context.last_question = None
        context.last_response = None
        context.processing = False
        context.state = BotState.AWAITING_QUESTION
        return context

    def try_begin_processing(self, user_id: int) -> bool:
        context = self.get_or_create(user_id)
        if context.processing:
            return False
        context.processing = True
        return True

    def finish_processing(self, user_id: int) -> None:
        self.get_or_create(user_id).processing = False

    def maybe_run_cleanup(self) -> int:
        return 0

    def run_cleanup(self, *, force: bool = False) -> int:
        return 0

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
    return TelegramUiService(config=config, rag_client=FakeRagClient(response), store=ConversationStoreStub())


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


def test_clarification_depth_exactly_limit_allows_last_clarification():
    service = _service({"needs_clarification": True, "clarification_options": ["Вариант 1"]})
    service.handle_command(1, "/start")
    first = service.handle_text(1, "1")
    assert "Уточните" in first[0].text
    second = service.handle_callback(1, "clarification:0")
    assert "Уточните" in second[0].text


def test_clarification_depth_exceeded_returns_controlled_fallback():
    service = _service({"needs_clarification": True, "clarification_options": ["Вариант 1"]})
    service.handle_command(1, "/start")
    service.handle_text(1, "1")
    service.handle_callback(1, "clarification:0")
    exceeded = service.handle_callback(1, "clarification:0")
    assert "Не удалось уточнить" in exceeded[0].text


def test_text_input_blocked_during_clarification_inline_only():
    service = _service({"needs_clarification": True, "clarification_options": ["Вариант 1", "Вариант 2"]})
    service.handle_command(1, "/start")
    service.handle_text(1, "Вопрос")

    blocked = service.handle_text(1, "свободный текст")
    assert "Сейчас нельзя отправить вопрос" in blocked[0].text


def test_debug_mode_renders_agent_trace_block():
    service = _service(
        {
            "summary": "ok",
            "details": "details",
            "sources": ["Doc A"],
            "confidence": 0.9,
            "debug": {
                "interpreted_query": "vacation policy",
                "top_k": 3,
                "chunks_used": 2,
                "coverage_ratio": 0.8,
                "model_context_window": 64000,
                "agent_trace": [
                    {"stage": "rewrite_agent", "latency_ms": 14},
                    {"stage": "retrieval_agent", "latency_ms": 28},
                ],
            },
        },
        enable_debug=True,
    )
    service.handle_command(99, "/start")
    service.handle_command(99, "/debug")

    result = service.handle_text(99, "Что в политике отпуска?")
    assert "🔍 Debug" in result[0].text
    assert "rewrite_agent: 14ms" in result[0].text
    assert "retrieval_agent: 28ms" in result[0].text


def test_debug_command_switches_debug_state_when_answer_available():
    service = _service({"summary": "ok", "details": "d", "sources": [], "confidence": 0.9}, enable_debug=True)
    service.handle_command(99, "/start")
    service.handle_text(99, "q")

    enabled = service.handle_command(99, "/debug")
    assert "включен" in enabled[0].text

    status = service.handle_command(99, "/status")
    assert "DEBUG" in status[0].text

    disabled = service.handle_command(99, "/debug")
    assert "выключен" in disabled[0].text
    status2 = service.handle_command(99, "/status")
    assert "ANSWER" in status2[0].text


def test_start_command_from_debug_state_is_safe():
    service = _service({"summary": "ok", "details": "d", "sources": [], "confidence": 0.9}, enable_debug=True)
    service.handle_command(99, "/start")
    service.handle_text(99, "q")
    service.handle_command(99, "/debug")

    start_again = service.handle_command(99, "/start")
    assert "Задайте вопрос" in start_again[0].text


def test_clarification_callback_rejects_non_numeric_index():
    service = _service({"needs_clarification": True, "clarification_options": ["A", "B"]})
    service.handle_command(1, "/start")
    service.handle_text(1, "Вопрос")

    bad = service.handle_callback(1, "clarification:not-a-number")
    assert "Некорректный выбор" in bad[0].text


def test_clarification_callback_honors_processing_lock():
    service = _service({"needs_clarification": True, "clarification_options": ["A", "B"]})
    service.handle_command(1, "/start")
    service.handle_text(1, "Вопрос")

    context = service.store.get_or_create(1)
    context.processing = True

    locked = service.handle_callback(1, "clarification:0")
    assert "Уже обрабатываю" in locked[0].text


def test_debug_command_in_awaiting_question_does_not_break_state_machine():
    service = _service({"summary": "ok", "details": "d", "sources": [], "confidence": 0.9}, enable_debug=True)
    service.handle_command(99, "/start")

    toggled = service.handle_command(99, "/debug")
    assert "включен" in toggled[0].text

    status = service.handle_command(99, "/status")
    assert "AWAITING_QUESTION" in status[0].text


def test_new_command_resets_dialog_state():
    service = _service({"summary": "ok", "details": "d", "sources": [], "confidence": 0.9})
    service.handle_command(1, "/start")
    service.handle_text(1, "Вопрос")

    reset = service.handle_command(1, "/new")
    assert "Новый диалог" in reset[0].text

    status = service.handle_command(1, "/status")
    assert "AWAITING_QUESTION" in status[0].text
    assert "0/2" in status[0].text


class CleanupAwareStore(ConversationStoreStub):
    def __init__(self):
        super().__init__()
        self.maybe_cleanup_calls = 0
        self.run_cleanup_calls = 0

    def maybe_run_cleanup(self) -> int:
        self.maybe_cleanup_calls += 1
        return 0

    def run_cleanup(self, *, force: bool = False) -> int:
        self.run_cleanup_calls += 1
        return 0


def test_opportunistic_cleanup_guard_runs_on_request_paths():
    config = UiConfig(rag_api_url="http://localhost:8000")
    store = CleanupAwareStore()
    service = TelegramUiService(config=config, rag_client=FakeRagClient({"summary": "ok", "details": "d", "sources": [], "confidence": 0.9}), store=store)

    service.handle_command(1, "/start")
    service.handle_text(1, "Вопрос")
    service.handle_callback(1, "analysis_details")

    assert store.maybe_cleanup_calls >= 3


def test_background_cleanup_task_runs_and_stops_gracefully():
    async def _run():
        config = UiConfig(rag_api_url="http://localhost:8000", fsm_cleanup_interval_seconds=0)
        store = CleanupAwareStore()
        service = TelegramUiService(config=config, rag_client=FakeRagClient({"summary": "ok", "details": "d", "sources": [], "confidence": 0.9}), store=store)

        await service.start_background_tasks()
        await asyncio.sleep(0.01)
        await service.stop_background_tasks()

        assert store.run_cleanup_calls >= 1

    asyncio.run(_run())
