# EPIC-7 Release Architecture

## REL-1: Production Docker build

`services/corporate-rag-service` now ships with a multi-stage Docker image:

1. **builder stage** installs Poetry dependencies and assembles runtime artifacts.
2. **runtime stage** copies only built artifacts, runs as a non-root `appuser`, and keeps a small final footprint.
3. `docker-entrypoint.sh` validates mandatory runtime environment variables before launching Uvicorn.

## Runtime validation contract

The container enforces:

- `APP_ENV` must be one of `production|staging|development`.
- `DATABASE_URL` must be set.
- `EMBEDDINGS_SERVICE_URL` must be set.

If validation fails, startup stops with a non-zero exit code.


## Discovery baseline (agent: `codebase-cartographer`)

### Module map (high-level)
- **Service A: `corporate-rag-service`**
  - API entrypoint: `app/api/routes.py`.
  - Business services: retrieval, reranking, context expansion, ingestion, anti-hallucination, security, telemetry.
  - Data layer: SQLAlchemy models + repositories + Alembic migrations.
  - External clients: embeddings service + Ollama.
- **Service B: `embeddings-service`**
  - API entrypoint: `app/api/routes.py`.
  - Encoder registry + model/dimension validation.
- **Frontend (`frontend/src`)**
  - Route pages: Query / Ingestion / Diagnostics.
  - API client layer and typed schemas.
  - UI components for conversation, trace, ingestion jobs, diagnostics.
- **Contracts**
  - OpenAPI specs: `openapi/rag.yaml`, `openapi/embeddings.yaml`.
  - Behavioral contracts: `docs/contracts/*.md`.

### Dependency boundaries
- `frontend` -> `corporate-rag-service` HTTP.
- `corporate-rag-service` -> `embeddings-service` HTTP.
- `corporate-rag-service` -> Ollama HTTP.
- `corporate-rag-service` -> Postgres/pgvector (+ optional object storage for ingestion artifacts).

### Discovery risk hotspots
- `app/api/routes.py` in `corporate-rag-service` has a very wide orchestration surface and mixed concerns (validation, orchestration, formatting, telemetry), making future refactors high-risk.
- Retrieval path combines lexical/vector/rerank/context-budget/memory boosting in one request flow; regression risk is concentrated in this chain.
- Contract drift is currently reported by the drift detector for endpoints/env vars/enums and must be treated as a controlled follow-up stream before large redesign work.
