# EPIC-08 / SP2 — Header Plumbing and Conversation Lifecycle

## Scope
SP2 introduces optional header parsing and gated conversation lifecycle behavior for `/v1/query`.

## Headers
- `X-Conversation-Id` (optional): UUID.
- `X-Client-Turn-Id` (optional): client idempotency identifier, persisted in user-turn meta when memory is enabled.

If `X-Conversation-Id` is present and invalid, endpoint returns HTTP 400 with error code:
- `B-CONV-ID-INVALID`

## Feature-flag behavior
- `USE_CONVERSATION_MEMORY=false`:
  - endpoint remains stateless
  - no read/write on conversation tables
- `USE_CONVERSATION_MEMORY=true` and valid `X-Conversation-Id`:
  - ensures conversation exists (create if absent)
  - updates `last_active_at`
  - if TTL exceeded (`CONVERSATION_TTL_MINUTES`), marks conversation as archived and continues with same `conversation_id`
  - persists one `user` turn and one `assistant` turn per request

## Notes
- No OpenAPI contract file changes.
- Existing response schema is unchanged.
- Repository tenant scoping is preserved via `ConversationRepository`.

## Windows smoke commands (SP2)
```bash
cd services/corporate-rag-service
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8420
curl -H "X-Conversation-Id: 11111111-1111-1111-1111-111111111111" http://localhost:8420/v1/query -d '{"query":"..."}'
```
