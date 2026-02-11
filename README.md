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
- Drift detector: `python scripts/drift_detector.py`
