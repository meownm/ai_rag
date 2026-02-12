from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .fsm import transition
from .models import BotState, UiConfig
from .renderer import OutboundMessage, assistant_messages, clarification_keyboard


class RAGClient(Protocol):
    def query(self, question: str, conversation_id: str) -> dict[str, Any]: ...


class ConversationStore(Protocol):
    def get_or_create(self, user_id: int, debug_default: bool = False): ...
    def update(self, user_id: int, updater): ...
    def reset_dialog(self, user_id: int): ...
    def try_begin_processing(self, user_id: int) -> bool: ...
    def finish_processing(self, user_id: int) -> None: ...


@dataclass(slots=True)
class TelegramUiService:
    config: UiConfig
    rag_client: RAGClient
    store: ConversationStore

    def handle_command(self, user_id: int, command: str) -> list[OutboundMessage]:
        context = self.store.get_or_create(user_id, debug_default=self.config.ui_debug_default)

        if command == "/start":
            if context.state != BotState.AWAITING_QUESTION:
                if context.state == BotState.DEBUG:
                    transition(context, BotState.ANSWER)
                if context.state != BotState.AWAITING_QUESTION:
                    transition(context, BotState.AWAITING_QUESTION)
            self.store.update(user_id, lambda c: setattr(c, "state", context.state))
            return [OutboundMessage("Привет! Задайте вопрос по документам.")]

        if command == "/new":
            self.store.reset_dialog(user_id)
            return [OutboundMessage("Новый диалог начат. Что хотите узнать?")]

        if command == "/sources":
            sources = context.last_response.get("sources", []) if context.last_response else []
            return [OutboundMessage("Последние источники:\n" + ("\n".join(sources) if sources else "Нет источников."))]

        if command == "/status":
            return [OutboundMessage(f"Состояние: {context.state}, уточнения: {context.clarification_depth}/{self.config.max_clarification_depth}")]

        if command == "/debug":
            if not self.config.enable_debug_command or user_id not in self.config.admin_user_ids:
                return [OutboundMessage("Команда недоступна.")]
            context.debug_enabled = not context.debug_enabled
            if context.debug_enabled and context.state == BotState.ANSWER:
                transition(context, BotState.DEBUG)
            elif not context.debug_enabled and context.state == BotState.DEBUG:
                transition(context, BotState.ANSWER)
            self.store.update(
                user_id,
                lambda c: (setattr(c, "debug_enabled", context.debug_enabled), setattr(c, "state", context.state)),
            )
            return [OutboundMessage(f"Debug {'включен' if context.debug_enabled else 'выключен'}.")]

        return [OutboundMessage("Неизвестная команда.")]

    def _process_question(self, context, text: str) -> list[OutboundMessage]:
        context.last_question = text
        transition(context, BotState.PROCESSING)
        self.store.update(
            context.user_id,
            lambda c: (setattr(c, "state", context.state), setattr(c, "last_question", text)),
        )
        try:
            response = self.rag_client.query(text, context.conversation_id)
            if response.get("needs_clarification"):
                if context.clarification_depth >= self.config.max_clarification_depth:
                    transition(context, BotState.ERROR)
                    self.store.update(context.user_id, lambda c: setattr(c, "state", context.state))
                    return [OutboundMessage("Не удалось уточнить вопрос. Начните новый диалог: /new")]
                context.pending_clarification = response.get("clarification_options", [])
                context.clarification_depth += 1
                transition(context, BotState.CLARIFICATION)
                self.store.update(
                    context.user_id,
                    lambda c: (
                        setattr(c, "state", context.state),
                        setattr(c, "pending_clarification", context.pending_clarification),
                        setattr(c, "clarification_depth", context.clarification_depth),
                    ),
                )
                return [OutboundMessage("Уточните запрос:", inline_keyboard=clarification_keyboard(context.pending_clarification))]

            confidence = float(response.get("confidence", 1.0))
            if confidence < 0.3:
                transition(context, BotState.ERROR)
                self.store.update(context.user_id, lambda c: setattr(c, "state", context.state))
                return [OutboundMessage("Недостаточно уверенности в ответе. Попробуйте переформулировать вопрос.")]

            transition(context, BotState.ANSWER)
            context.last_response = response
            self.store.update(
                context.user_id,
                lambda c: (setattr(c, "state", context.state), setattr(c, "last_response", response)),
            )
            debug_block = None
            if context.debug_enabled:
                debug_data = response.get("debug", {})
                agent_trace = debug_data.get("agent_trace", [])
                agent_trace_lines = []
                for stage in agent_trace:
                    if isinstance(stage, dict):
                        agent_trace_lines.append(f"- {stage.get('stage', '?')}: {stage.get('latency_ms', '?')}ms")
                agent_trace_text = "\n".join(agent_trace_lines) if agent_trace_lines else "-"
                debug_block = (
                    f"interpreted_query: {debug_data.get('interpreted_query', '-') }\n"
                    f"top_k: {debug_data.get('top_k', '-') }\n"
                    f"chunks_used: {debug_data.get('chunks_used', '-') }\n"
                    f"coverage_ratio: {debug_data.get('coverage_ratio', '-') }\n"
                    f"model_context_window: {debug_data.get('model_context_window', '-') }\n"
                    f"confidence: {response.get('confidence', '-') }\n"
                    f"agent_trace:\n{agent_trace_text}"
                )
            return assistant_messages(
                answer=response.get("summary", "Ответ не найден."),
                details=response.get("details", ""),
                sources=response.get("sources", []),
                context=context,
                debug_block=debug_block,
            )
        except Exception:
            transition(context, BotState.ERROR)
            self.store.update(context.user_id, lambda c: setattr(c, "state", context.state))
            return [OutboundMessage("Произошла ошибка при обработке запроса. Попробуйте позже.")]
        finally:
            self.store.finish_processing(context.user_id)

    def handle_text(self, user_id: int, text: str) -> list[OutboundMessage]:
        context = self.store.get_or_create(user_id, debug_default=self.config.ui_debug_default)
        if not self.store.try_begin_processing(user_id):
            return [OutboundMessage("⏳ Уже обрабатываю предыдущий запрос.")]

        if context.state == BotState.IDLE:
            transition(context, BotState.AWAITING_QUESTION)
            self.store.update(user_id, lambda c: setattr(c, "state", context.state))

        if context.state not in {BotState.AWAITING_QUESTION, BotState.ANSWER, BotState.DEBUG}:
            self.store.finish_processing(user_id)
            return [OutboundMessage("Сейчас нельзя отправить вопрос. Используйте /new.")]

        return self._process_question(context, text)

    def handle_callback(self, user_id: int, callback_data: str) -> list[OutboundMessage]:
        context = self.store.get_or_create(user_id, debug_default=self.config.ui_debug_default)

        if callback_data == "new_dialog":
            self.store.reset_dialog(user_id)
            return [OutboundMessage("Диалог сброшен. Задайте новый вопрос.")]

        if callback_data.startswith("clarification:"):
            if callback_data.endswith("cancel"):
                transition(context, BotState.AWAITING_QUESTION)
                self.store.update(user_id, lambda c: setattr(c, "state", context.state))
                return [OutboundMessage("Уточнение отменено.")]

            if context.state != BotState.CLARIFICATION:
                return [OutboundMessage("Нет активного уточнения.")]

            raw_index = callback_data.split(":", 1)[1]
            if not raw_index.isdigit():
                return [OutboundMessage("Некорректный выбор уточнения.")]
            index = int(raw_index)
            if index >= len(context.pending_clarification):
                return [OutboundMessage("Некорректный выбор уточнения.")]
            if not self.store.try_begin_processing(user_id):
                return [OutboundMessage("⏳ Уже обрабатываю предыдущий запрос.")]
            option = context.pending_clarification[index]
            return self._process_question(context, option)

        if callback_data == "analysis_details":
            if not context.last_response:
                return [OutboundMessage("Детали анализа пока недоступны.")]
            return [OutboundMessage(context.last_response.get("details", "Детали отсутствуют."))]

        if callback_data == "similar_topics":
            suggestions = context.last_response.get("followup", []) if context.last_response else []
            rendered = "\n".join(f"• {item}" for item in suggestions) if suggestions else "Нет предложений"
            return [OutboundMessage(f"Похожие темы:\n{rendered}")]

        return [OutboundMessage("Неизвестное действие.")]
