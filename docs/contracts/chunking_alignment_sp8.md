# SP8 — Chunking alignment with `chunking_spec_v1.md`

## Parameters
- `CHUNK_TARGET_TOKENS=650`
- `CHUNK_MAX_TOKENS=900`
- `CHUNK_MIN_TOKENS=120`
- `CHUNK_OVERLAP_TOKENS=80`

## Behavior
- Markdown is parsed into deterministic typed blocks (`paragraph`, `list`, `table`, `code`, `quote`) with heading path tracking.
- Chunk assembly uses target/min/max token budgets and overlap splitting for paragraph/mixed content.
- Metadata persisted for new chunks:
  - `chunk_type`
  - `char_start`, `char_end`
  - `block_start_idx`, `block_end_idx`

## Database migration
- Adds nullable metadata columns to `chunks` table so existing rows remain valid.
- Backfill strategy for existing rows: leave metadata as `NULL`; metadata is populated for new ingestions.

## Stability
- Stable `chunk_id` semantics are preserved because IDs still derive from canonical chunk text + ordinal + document/version identifiers.
