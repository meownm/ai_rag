# UI Conversational Layer (Telegram + Web) v1.0

## Scope
- `telegram-bot-service` UI-only FSM and rendering layer.
- `web-frontend` conversational analytical interface.
- No OpenAPI changes in `openapi/rag.yaml`.

## Telegram UI Layer
Implemented in `services/telegram-bot-service/telegram_ui`:
- FSM states: `IDLE`, `AWAITING_QUESTION`, `PROCESSING`, `CLARIFICATION`, `ANSWER`, `ERROR`, `DEBUG`.
- Transition guards with invalid-transition protection.
- Per-user isolated context storage backed by PostgreSQL (`telegram_conversations`) via `PostgresConversationStore` with atomic row-level transitions.
- Atomic processing lock per user (`try_begin_processing` / `finish_processing`) to prevent concurrent `PROCESSING` in both text and clarification-callback flows.
- Clarification depth limit via `max_clarification_depth` and inline-button-only clarification path (free-text blocked while in `CLARIFICATION`), with malformed clarification callback guard.
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
- Optional debug panel (settings toggle + role gating), including `agent_trace` stage/latency rendering when provided by backend debug payload, and safe `/start` behavior when debug mode is active.
- Clarification modal with radio-only options (no free text in modal path).
- Friendly error mapping, including context overflow and network cases.

## Testing coverage updates
- Telegram unit tests for FSM transitions/invalid transitions, PostgreSQL store persistence/locking, TTL cleanup and renderer split safety.
- Telegram integration-style tests for commands, clarification depth, malformed callback handling, inline-only clarification UX, debug gate/state safety, debug trace rendering, and low confidence handling.
- Web tests for structured rendering, clarification modal behavior, debug rendering, and refusal/error safety.

## Notes
- Redis dependency removed from Telegram FSM path; state is fully PostgreSQL-backed and restart-safe.
- In-app cleanup worker removes stale FSM rows without cron using `TELEGRAM_FSM_TTL_HOURS` (default `24`) and `TELEGRAM_FSM_CLEANUP_INTERVAL_SECONDS` (default `1800`).
- Opportunistic cleanup guard runs on request path if background cleanup loop is unavailable, throttled by interval.
- Conversational logic remains UI-layer local and backend-compatible.


## EPIC-4 Web UI implementation (WEB-1..WEB-5)

1. **WEB-1 Layout**
   - Two-column main layout (`chat + sources sidebar`) retained and validated.
   - Header includes `New Dialog` and `Settings` actions.
   - Input area is sticky at the bottom for long chat sessions.
   - `New Dialog` now resets transient clarification/source-preview state.
2. **WEB-2 Structured chat components**
   - Assistant message rendering decomposed into `SummaryBlock`, `DetailsBlock`, `SourcesBlock`.
3. **WEB-3 Sources sidebar**
   - Sidebar lists used documents and supports preview modal open by source click.
   - Preview modal now highlights matching token(s) from the latest query in snippet content when possible.
4. **WEB-4 Debug transparency panel**
   - Debug panel includes agent trace lines, coverage ratio, and dynamic `top_k`.
5. **WEB-5 Clarification modal**
   - Clarification flow is radio-selection-only with explicit apply action (`Применить`), with disabled apply until a variant is selected.

### EPIC-4 tests
- Positive + negative UI tests updated in `frontend/src/test/query-page.test.tsx`:
  - structured blocks render,
  - clarification modal blocks direct send and applies radio selection,
  - debug panel fields and agent trace rendering,
  - source preview modal highlight behavior,
  - new dialog reset behavior.
