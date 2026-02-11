# UI Conversational Layer (Telegram + Web) v1.0

## Scope
- `telegram-bot-service` UI-only FSM and rendering layer.
- `web-frontend` conversational analytical interface.
- No OpenAPI changes in `openapi/rag.yaml`.

## Telegram UI Layer
Implemented in `services/telegram-bot-service/telegram_ui`:
- FSM states: `IDLE`, `AWAITING_QUESTION`, `PROCESSING`, `CLARIFICATION`, `ANSWER`, `ERROR`, `DEBUG`.
- Transition guards with invalid-transition protection.
- Per-user isolated context storage with in-memory thread-safe store.
- Processing lock per user to avoid parallel `PROCESSING`.
- Clarification depth limit via `max_clarification_depth`.
- Command layer:
  - `/start`, `/new`, `/sources`, `/status`, `/debug` (admin + feature flag only).
- Structured rendering:
  - `summary`, `details`, `sources`.
  - Telegram-safe chunking under 3500 chars.
  - Inline actions:
    - 🔁 Уточнить
    - 📚 Похожие темы
    - 🆕 Новый диалог
    - ℹ️ Детали анализа
- Friendly error responses, no stack traces leaked.

## Web UI Layer
Implemented in `frontend/src/pages/QueryPage.tsx` and `frontend/src/components/conversation`:
- Header actions: New Dialog, Sources, Settings.
- Two-column responsive main area: ChatPanel + SourcesPanel.
- Footer input field pinned in page layout.
- Structured assistant message:
  - SummaryBlock
  - DetailsBlock
  - SourcesBlock
- Sources panel with used documents list.
- Chunk preview modal for source snippet inspection.
- Optional debug panel (settings toggle + role gating).
- Clarification modal with radio-only options (no free text in modal path).
- Friendly error mapping, including context overflow and network cases.

## Testing coverage updates
- Telegram unit tests for FSM transitions and invalid transitions.
- Telegram integration-style tests for commands, clarification, depth limit, debug gate, and low confidence handling.
- Web tests for structured rendering, clarification modal behavior, debug rendering, and refusal/error safety.

## Notes
- Redis persistence is intentionally abstracted behind in-memory store in this increment (fallback mode).
- Conversational logic remains UI-layer local and backend-compatible.
