# EPIC-08 / SP5 — Clarification Loop Contract

## Scope
SP5 enables interactive disambiguation when rewrite confidence is low and clarification is needed.

## Enablement conditions
Clarification behavior is active only when all are true:
- `USE_CLARIFICATION_LOOP=true`
- `USE_LLM_QUERY_REWRITE=true`
- `USE_CONVERSATION_MEMORY=true`

## Clarification trigger
If rewrite result indicates:
- `clarification_needed=true`
- `confidence < REWRITE_CONFIDENCE_THRESHOLD`

Then the service:
- returns `clarification_question` as the response `answer`
- skips embeddings/retrieval/generation for that turn
- persists `query_resolutions` with clarification fields
- persists assistant clarification turn

## Follow-up handling
On next user turn for same conversation:
- latest unresolved clarification is detected via `query_resolutions`
- rewriter receives:
  - `clarification_pending=true`
  - `last_question=<last clarification question>`

## Loop guard
To prevent infinite loops:
- max 2 consecutive clarification turns per conversation
- after streak reaches 2, pipeline proceeds to retrieval path

## Compatibility
- No OpenAPI changes.
- Flags off preserve prior behavior.
