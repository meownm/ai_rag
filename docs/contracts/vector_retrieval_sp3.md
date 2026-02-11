# Vector retrieval contract notes (EPIC-07 SP3)

## Feature flag
- `USE_VECTOR_RETRIEVAL=false` (default): preserve legacy ordinal candidate selection.
- `USE_VECTOR_RETRIEVAL=true`: enable pgvector similarity retrieval.

## Retrieval behavior
- Legacy mode (`false`): vector candidates are selected by `chunks.ordinal ASC`.
- Similarity mode (`true`): vector candidates are selected by pgvector L2 distance:
  - `ORDER BY chunk_vectors.embedding <-> :query_embedding ASC`
  - candidate score uses `1 / (1 + distance)`.

## Indexing support
Alembic revision `0004_add_chunk_vectors_ann_index` adds a conditional ANN index on `chunk_vectors.embedding`:
- Prefer `hnsw` (`vector_l2_ops`) when supported.
- Fallback to `ivfflat` (`vector_l2_ops`) when available.
- No-op if pgvector access method support is unavailable.
