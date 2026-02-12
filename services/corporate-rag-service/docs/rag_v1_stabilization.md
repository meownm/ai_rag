# RAG v1 Stabilization Notes

## Configuration Consistency

- `MODEL_CONTEXT_WINDOW` must be exactly equal to `LLM_NUM_CTX`.
- `MAX_CONTEXT_TOKENS` must be less than or equal to `LLM_NUM_CTX`.
- Token-budget assembly is enabled by default and word-based context trimming is disabled.
- Vector retrieval is enabled by default.

## Startup Validation

At startup the service now:

1. Validates model context windows against provider metadata.
2. Emits a structured warning log (`startup_vector_retrieval_disabled_with_pgvector`) if `PGVECTOR_ENABLED=true` while vector retrieval is disabled.

## Ingestion Structure Preservation

### DOCX

- Paragraphs and tables are processed in native document order.
- Heading levels are preserved in markdown (`#`, `##`, ...).
- List paragraphs are emitted with markdown list markers and preserve nested indentation via DOCX `numPr/ilvl` (including `numPr` fallback when style names are generic).
- Tables remain in-place instead of being appended at document end.

### PDF

- Extraction uses `pdfplumber` and preserves paragraph boundaries.
- Page markers are always emitted (`<!-- page:N -->`).
- Basic tables are converted to markdown tables when at least two rows are detected.

## Ingestion Runtime Unification

- `/v1/ingest/files/upload` now uses the same connector registry ingestion path as other source types (`ingest_sources_sync` + `SourceConnector`).
- Byte uploads are no longer blocked by legacy `NotImplementedError`; upload ingestion passes through connector descriptors/fetch flow and stores raw payload artifacts.
- Deprecated connector stubs were removed from runtime scope; default connector registration contains only real connectors.

## Windows Scripts

- `run_local.bat` reads `PORT` from `.env`, sets window title, prints Swagger URL before `uvicorn` startup, and pauses on error.
- `deploy_docker_desktop.bat` reads `RAG_SERVICE_PORT` from `.env`, avoids hardcoded port assumptions, prints Swagger URL, and pauses on error.

## Production Critical Hardening

### SP1 — Tombstone safety on capped listings

- Connector tombstone deletion now runs only when connector contract explicitly returns `listing_complete=true`.
- Any non-authoritative listing (`listing_complete=false`) skips tombstone deletion regardless of descriptor count.

### SP2 — Version-aware S3 object layout

- New ingestion writes raw, markdown, and artifact objects under `tenant_id/source_id/source_version_id/...`.
- Different `source_version_id` values produce deterministic, distinct S3 paths for auditability.
- Existing versions remain backward-compatible because persisted URIs in `source_versions` are still used for retrieval.

### SP3 — `chunk_vectors.updated_at` consistency

- Added `updated_at timestamptz NOT NULL DEFAULT now()` to `chunk_vectors` via Alembic migration.
- ORM model now includes `updated_at`, aligned with vector UPSERT logic (`updated_at = now()` on conflict).

### SP4 — Unique document per source version

- Added DB unique constraint `uq_documents_tenant_source_version (tenant_id, source_version_id)` with migration-time duplicate cleanup that first re-links dependent rows (`chunks`, `document_links`, `cross_links`) to the kept document to preserve existing data.
- `_insert_document` now uses `INSERT ... ON CONFLICT DO NOTHING RETURNING document_id`; on conflict it resolves existing `document_id` without creating duplicates.

### SP5 — Tenant isolation in `document_links`

- Added `tenant_id` to `document_links` with migration backfill from `documents` and index `ix_document_links_tenant_id`.
- Link insertion now writes `tenant_id` on every row, enabling tenant-scoped joins and preventing cross-tenant leakage.

## v1.1 Quality Hardening

### SP1 — Nested DOCX list hierarchy

- Ordered list numbering is now tracked independently per `(numId, ilvl)` from DOCX XML to prevent flattening and cross-level counter bleed.
- Three-level bullet, numbered, and mixed list structures are covered by ingestion tests.

### SP2 — Deterministic hybrid scoring

- Hybrid retrieval now uses configurable weighted merge (`HYBRID_WEIGHT_VECTOR=0.7`, `HYBRID_WEIGHT_FTS=0.3` by default).
- Vector and FTS scores are normalized into `[0,1]` before merge when normalization is enabled.
- Candidate deduplication by `chunk_id` happens before ranking, and final ordering is deterministic: `final_score DESC`, `chunk_id ASC`.

### SP3 — Document-aware context expansion caps

- Added `CONTEXT_EXPANSION_MAX_EXTRA_PER_DOC` to avoid over-expanding one document.
- Expansion debug now reports `expanded_total` and per-document counts via `expanded_per_doc`.

### SP4 — Strict context token budget enforcement

- Context assembly re-computes token totals and deterministically trims lowest-scored chunks until within budget.
- Budget logs include `initial_tokens`, `trimmed_tokens`, and `final_tokens` for diagnostics.

### SP5/SP6 — Conversation history controls

- Added strict bounds: `MAX_HISTORY_TURNS` and `MAX_HISTORY_TOKENS`.
- Topic reset heuristic compares embedding similarity between current query and previous user turn; when below `TOPIC_RESET_SIMILARITY_THRESHOLD`, history is excluded from rewrite context and `topic_reset` is logged.

### SP7 — Citation safety

- LLM citation payload is validated against retrieved `chunk_id` set.
- Any citation outside retrieved chunks is treated as invalid and triggers insufficient-evidence handling.

### Review follow-up hardening

- Hybrid merge now exposes `hybrid_score` and sets `final_score` strictly by weighted normalized vector/FTS formula for deterministic reproducibility.
- Added stronger hybrid settings validation (`0..1` bounds + exact sum to `1.0`).
- Neighbor-only expansion mode now also reports per-document expansion counters in debug metrics.
- Added integration coverage for deterministic `hybrid_rank -> apply_context_budget` flow and topic-reset/citation-safety guard behavior.

## Quality hardening updates

- DOCX ingestion now keeps consecutive list paragraphs as a single markdown list block and supports configurable indentation via `DOCX_LIST_INDENT_SPACES`.
- Hybrid retrieval uses normalized channels in `[0,1]`, weighted by `HYBRID_W_VECTOR` and `HYBRID_W_FTS`, with deterministic tie-break `(final desc, source_preference desc, chunk_id asc)`.
- Candidate windows are configurable with `HYBRID_MAX_VECTOR` and `HYBRID_MAX_FTS`.
- Context expansion is controlled by `EXPAND_NEIGHBORS_ENABLED`, `EXPAND_NEIGHBORS_WINDOW`, `EXPAND_MAX_EXTRA_TOTAL`, and `EXPAND_MAX_EXTRA_PER_DOC`.
- Token budget enforcement applies `TOKEN_BUDGET_SAFETY_MARGIN` and deterministic tail truncation when needed.
- Topic reset can be toggled with `TOPIC_RESET_ENABLED` and thresholded by `TOPIC_RESET_SIM_THRESHOLD`.
- Citation validation now requires `(chunk_id, document_id)` pairs to exist in the selected context allowlist.


## INT-SP2 Immutable Versioned Storage

- Raw payload is stored only as immutable `raw.bin` under `tenant_id/source_id/source_version_id/`.
- Manual writes to versioned raw keys (`tenant/source/source_version/raw.bin`) and immutable object rewrites now fail fast with deterministic `VersionOverwriteError` when key already exists.
- Ingestion requires immutable storage methods (`put_bytes_immutable`, `put_text_immutable`) and fails fast if unavailable.
- `source_versions.checksum` is enforced from raw content bytes to avoid duplicate identical versions while preserving new versions for changed content.
- Existing historical data remains readable because persisted `s3_raw_uri`/`s3_markdown_uri` values are unchanged (no destructive migration).
