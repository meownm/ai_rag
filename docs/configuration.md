# Configuration normalization (EPIC-CONFIG-CONSOLIDATION)

## Stop point CFG-SP1 — inventory matrix

### corporate-rag-service

| Variable | Status | Notes |
|---|---|---|
| `SERVICE_PORT` | used | Canonical service port. |
| `RAG_SERVICE_PORT` | deprecated alias | Supported for one release cycle with warning. |
| `PORT` | deprecated alias | Supported for one release cycle with warning. |
| `LLM_PROVIDER` | used | Canonical provider selector (`ollama\|openai\|other`). |
| `LLM_ENDPOINT` | used | Canonical LLM endpoint. |
| `LLM_MODEL` | used | Canonical LLM model. |
| `OLLAMA_BASE_URL` | deprecated alias | Mapped to `LLM_ENDPOINT`, warning logged. |
| `OLLAMA_MODEL` | deprecated alias | Mapped to `LLM_MODEL`, warning logged. |
| `DEFAULT_TOP_K` | used | Canonical retrieval default. |
| `RERANKER_TOP_K` | used | Canonical reranker top-k. |

### embeddings-service

| Variable | Status | Notes |
|---|---|---|
| `SERVICE_PORT` | used | Canonical service port. |
| `EMBEDDINGS_SERVICE_PORT` | deprecated alias | Supported for one release cycle with warning. |
| `PORT` | deprecated alias | Supported for one release cycle with warning. |
| `LLM_PROVIDER` | used | Canonical provider selector. |
| `LLM_ENDPOINT` | used | Canonical LLM endpoint. |
| `LLM_MODEL` | used | Canonical model name/id. |
| `OLLAMA_BASE_URL` | deprecated alias | Mapped to `LLM_ENDPOINT`, warning logged. |
| `OLLAMA_MODEL` | deprecated alias | Mapped to `LLM_MODEL`, warning logged. |
| `DEFAULT_MODEL_ID` | deprecated alias | Mapped to `LLM_MODEL`, warning logged. |

### frontend

| Variable | Status | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | used | API base URL in `frontend/src/lib/env.ts`. |
| `VITE_UI_MODE` | used | UI mode (`prod`/`debug`). |

## Stop points CFG-SP2..SP6 decisions

- LLM config is unified on `LLM_PROVIDER`, `LLM_ENDPOINT`, `LLM_MODEL`.
- Port config is unified on `SERVICE_PORT`.
- Retrieval top-k is unified on `DEFAULT_TOP_K` and `RERANKER_TOP_K`.
- Deprecated aliases emit startup warnings and are conflict-validated.
- Startup validation fails fast for conflicting alias values.

## Remaining feature flags

The following feature flags remain active and code-referenced:

- `USE_VECTOR_RETRIEVAL`
- `USE_CONTEXTUAL_EXPANSION`
- `USE_TOKEN_BUDGET_ASSEMBLY`
- `USE_LLM_GENERATION`
- `USE_CONVERSATION_MEMORY`
- `USE_LLM_QUERY_REWRITE`
- `USE_CLARIFICATION_LOOP`
- `CONNECTOR_REGISTRY_ENABLED`
- `CONNECTOR_INCREMENTAL_ENABLED`
- `ENABLE_PER_STAGE_LATENCY_METRICS`


## Backward-compatibility window (one release cycle)

Deprecated aliases remain accepted and log warnings at startup. In `embeddings-service`, legacy unused variables are tolerated and ignored (with warning) to avoid breaking existing `.env` files during migration.

Ignored legacy keys in `embeddings-service` include:
`RERANKER_MODEL`, `RERANKER_TOP_K`, `DEFAULT_TOP_K`, `REQUEST_TIMEOUT_SECONDS`, `EMBEDDINGS_TIMEOUT_SECONDS`, `MAX_EMBED_BATCH_SIZE`, `DB_*`, `DATABASE_URL`, `PGVECTOR_ENABLED`, `S3_*`, `EMBEDDINGS_SERVICE_URL`.
