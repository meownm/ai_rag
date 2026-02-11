# EPIC-08 / SP3 — LLM Query Rewriter Contract

## Scope
SP3 adds optional query rewriting before retrieval in `services/corporate-rag-service`.

## Feature flag
- `USE_LLM_QUERY_REWRITE=false` (default): bypass rewriter and use raw `query`.
- `USE_LLM_QUERY_REWRITE=true`: invoke rewriter and use `resolved_query_text` in embeddings/retrieval/rerank.

## Rewriter module
- File: `app/runners/query_rewriter.py`
- Input fields:
  - `tenant_id`
  - `conversation_id` (nullable)
  - `user_query`
  - `recent_turns`
  - `summary` (optional)
  - `citation_hints` (optional)
- Output type: `QueryRewriteResult`

## Strict JSON schema validation
Rewriter output is validated against JSON Schema (`Draft 2020-12`) with required fields:
- `resolved_query_text` (string, minLength=1)
- `follow_up` (boolean)
- `topic_shift` (boolean)
- `intent` (string)
- `entities` (array of `{type,value}`)
- `clarification_needed` (boolean)
- `clarification_question` (string|null)
- `confidence` (number in `[0,1]`)

If validation or parsing fails while flag is enabled:
- return HTTP 502 with `error.code = B-REWRITE-FAILED`
- no silent fallback to raw query.

## LLM call requirements
- Uses existing `OllamaClient`.
- Enforces `keep_alive = REWRITE_KEEP_ALIVE`.
- Logs control-plane entries with rewrite model and keep_alive via `LLM_REQUEST` / `LLM_RESPONSE`.

## Persistence
When rewrite is used and conversation memory context is available:
- write `query_resolutions` record via `ConversationRepository.create_query_resolution`.
- persist rewrite inputs and confidence.

## Compatibility
- No OpenAPI changes.
- Retrieval path remains unchanged when rewrite flag is off.
