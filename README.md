# AI RAG Monorepo

## Services
- `services/corporate-rag-service` - multi-tenant RAG orchestration API.
- `services/embeddings-service` - dedicated embeddings API.

## Quick start
1. Copy `.env.example` to `.env` in each service.
2. Install dependencies with Poetry.
3. Run each service with Uvicorn.

## Validation
- Corporate service tests: `cd services/corporate-rag-service && poetry run pytest`
- Embeddings service tests: `cd services/embeddings-service && poetry run pytest`
- Drift detector (includes dependency alignment checks for shared Python runtime packages): `python scripts/drift_detector.py`

## Embeddings service configuration
- `EMBEDDINGS_DEFAULT_MODEL_ID` (default: `bge-m3`) — model used when `POST /v1/embeddings` payload omits `model`.
- `EMBEDDING_DIM` (default: `1024`) — expected embedding vector dimension; mismatches return HTTP 422 with `E-EMB-DIM-MISMATCH`.
- Diagnostics endpoint: `GET /v1/healthz` returns `status`, `default_model_id`, `embedding_dim`, and `loaded_models`.


## Corporate RAG feature flags
- `USE_VECTOR_RETRIEVAL` (default: `false`) — enables pgvector similarity retrieval when true.
- `HYBRID_SCORE_NORMALIZATION` (default: `false`) — enables normalized lexical/vector score fusion when true.
- `USE_CONTEXTUAL_EXPANSION` (default: `false`) and `NEIGHBOR_WINDOW` (default: `1`) — enables neighbor chunk expansion.
- `USE_TOKEN_BUDGET_ASSEMBLY` (default: `false`) and `MAX_CONTEXT_TOKENS` (default: `8000`) — enables token-budget context assembly.
- `USE_LLM_GENERATION` (default: `false`) — keeps retrieval-only answer construction by default; when true calls LLM generation mode with `keep_alive=0`.
- `CHUNK_TARGET_TOKENS` (`650`), `CHUNK_MAX_TOKENS` (`900`), `CHUNK_MIN_TOKENS` (`120`), `CHUNK_OVERLAP_TOKENS` (`80`) — chunking parameters aligned with `chunking_spec_v1.md`.

