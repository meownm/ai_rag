# Contextual expansion notes (EPIC-07 SP5)

## Feature flags
- `USE_CONTEXTUAL_EXPANSION=false` (default): preserve existing top-k only behavior.
- `USE_CONTEXTUAL_EXPANSION=true`: include neighbor chunks around top hits.
- `NEIGHBOR_WINDOW=1` (default): neighbor radius by ordinal on each side.

## Expansion behavior
When enabled:
- For each top chunk, fetch chunks with ordinal in `[ordinal - NEIGHBOR_WINDOW, ordinal + NEIGHBOR_WINDOW]` in the same document.
- Merge overlap windows across multiple top chunks.
- De-duplicate by `chunk_id`.
- Preserve deterministic order by `(document_id, ordinal, chunk_id)`.

## Citations
Expanded chunks are included in `citations` with existing fields (`document_id`, `chunk_id`, snippet, scores) without schema changes.
