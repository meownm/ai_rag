# Embedding indexing contract notes (EPIC-07 SP2)

## Scope
`services/corporate-rag-service` ingestion pipeline now indexes chunk embeddings in batches via `embeddings-service`.

## Runtime knobs
- `EMBEDDINGS_SERVICE_URL` (default: `http://localhost:8200`)
- `EMBEDDINGS_DEFAULT_MODEL_ID` (default: `bge-m3`)
- `EMBEDDINGS_BATCH_SIZE` (default: `64`)
- `EMBEDDINGS_RETRY_ATTEMPTS` (default: `3`)

## Behavioral details
- After chunk insertion, vector indexing selects only non-indexed chunks using `LEFT JOIN chunk_vectors ... WHERE cv.chunk_id IS NULL` with tenant filtering.
- Embeddings requests are sent in batches (`input: [..]`) using one HTTP call per batch.
- Inserts use `ON CONFLICT (chunk_id) DO UPDATE` and refresh `updated_at` to keep idempotent behavior.
- On repeated upstream failures after bounded retries, ingestion raises `S-EMB-INDEX-FAILED`.

## Observability
- Ingestion emits control-plane completion log fields:
  - `vectors_indexed_count`
  - `batch_count`
  - `duration_ms`
- Data-plane event payloads for embedding indexing include chunk ids and dimensions, but not full chunk text.
