# Architecture

## High-level components
- **Infra**
  - PostgreSQL (+ pgvector, pg_stat_statements)
  - MinIO (S3-compatible object storage)
  - PGHero (DB visibility)
- **Core services** (planned)
  - `document-registry-service` — document metadata, versions, access checks
  - `document-processor-service` — extraction, normalization, conversion
  - `embedding-worker` — chunking + embeddings
  - `search-api` — FTS, vector, hybrid retrieval
  - `rag-api` — response synthesis with strict structured output
- **Interfaces** (planned)
  - Telegram Bot
  - Web UI
  - Telegram Mini App

## Data flow (target)
1. Source file is registered (metadata) + stored in MinIO
2. Text is extracted and normalized, stored in PostgreSQL
3. Chunks are produced and embedded; vectors stored in pgvector
4. Search API runs FTS + vector retrieval + hybrid ranking
5. RAG API composes answer from retrieved passages under policy and outputs structured JSON

## Boundaries
- Ingestion does not depend on embeddings, search, or LLM
- Search does not depend on LLM
- RAG depends on search only (not on UI)
- UI depends on APIs only
