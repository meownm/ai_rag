# Unified Connector Contracts

## Interfaces

- `SourceConnector` exposes:
  - `is_configured() -> (bool, reason)`
  - `list_descriptors(tenant_id, sync_context) -> list[SourceDescriptor]`
  - `fetch_item(tenant_id, descriptor) -> ConnectorFetchResult`
- `SourceDescriptor` is metadata-only and must provide stable `external_ref` per `source_type` and tenant.
- `SourceItem.markdown` is the canonical ingestion input.

## Invariants

1. `external_ref` is deterministic and unique in `(tenant_id, source_type)`.
2. Connector metadata must be JSON-serializable and bounded (errors are truncated to 512 chars).
3. Incremental decisions are deterministic for the same descriptor/state snapshot.

## Idempotency

- If descriptor `last_modified` and `checksum_hint` are unchanged, ingestion is skipped when incremental mode is on.
- Source sync state is updated atomically per item using upsert semantics.
- Re-running with unchanged snapshots must not create new `source_versions`.


## Confluence pages connector

- Uses two-step retrieval: `list_pages` via `/rest/api/content/search` **without** body expansion, then `fetch_page_body_by_id` with `expand=body.<representation>,version,history`.
- `external_ref` format: `page:{id}`.
- Storage/view HTML body is converted to Markdown with deterministic table rendering (including `rowspan/colspan` normalization).

- Macros are sanitized deterministically:
  - code macro -> fenced code block with language,
  - info/note macros -> blockquote with label,
  - unsupported macros -> stable placeholder.
- Nested list depth and heading hierarchy are preserved in rendered markdown.
- Inline attachment references are emitted as markdown links (`attachment:<filename>`).

- Backward-compatibility guard: when explicit legacy crawler instances are passed to `ingest_sources_sync`, ingestion uses that legacy path to avoid breaking existing call sites/tests while registry mode remains default for normal runtime dispatch.
