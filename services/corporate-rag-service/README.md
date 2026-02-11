# corporate-rag-service

## EPIC-08 Conversational RAG flags

The following environment variables were added for conversational memory, rewriting, clarification loop, and summarization. Defaults preserve stateless behavior.

- `USE_CONVERSATION_MEMORY=false`
- `USE_LLM_QUERY_REWRITE=false`
- `USE_CLARIFICATION_LOOP=false`
- `CONVERSATION_TURNS_LAST_N=8`
- `CONVERSATION_SUMMARY_THRESHOLD_TURNS=12`
- `CONVERSATION_TTL_MINUTES=30`
- `REWRITE_CONFIDENCE_THRESHOLD=0.55`
- `REWRITE_MODEL_ID=qwen3:14b-instruct`
- `REWRITE_KEEP_ALIVE=0`
- `REWRITE_MAX_CONTEXT_TOKENS=2048`

See also `.env.example` for runnable defaults.

## Windows smoke test

```powershell
cd services/corporate-rag-service
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8420
curl -H "X-Conversation-Id: 11111111-1111-1111-1111-111111111111" http://localhost:8420/v1/query -d '{"query":"..."}'
```
