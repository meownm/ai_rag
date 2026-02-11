# EPIC-08 / SP6 — Conversation Summarization Contract

## Scope
SP6 introduces conversation summaries to keep rewrite prompts within a bounded context size.

## Trigger
For conversation-aware requests (`USE_CONVERSATION_MEMORY=true` with valid conversation header):
- when available turns reach `CONVERSATION_SUMMARY_THRESHOLD_TURNS`
- service creates/updates a summary in `conversation_summaries`
- summary version increments monotonically per conversation

## Summarizer
- Module: `app/runners/conversation_summarizer.py`
- Reuses existing LLM infrastructure (`OllamaClient`) in plain mode
- Produces short plain-text summary for rewrite context

## Masked-mode safety
When `LOG_DATA_MODE=masked`:
- summary generation avoids storing direct user quotes
- stored summary is high-level metadata-oriented and excludes raw sensitive snippets

## Rewrite integration
- rewriter loads latest available summary via `ConversationRepository.get_latest_summary(...)`
- summary is passed as `ConversationSummary` context in rewrite prompt

## Compatibility
- No OpenAPI changes.
- Flags off preserve existing behavior.
