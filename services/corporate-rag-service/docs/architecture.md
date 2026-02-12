# Architecture

## Connector Layer

Ingestion now routes source discovery/fetch through a connector registry (`app/services/connectors`).

- Registry can be disabled via `CONNECTOR_REGISTRY_ENABLED=false`.
- Supported source types are registered centrally and validated per run.
- Unknown and not-configured source types return deterministic error codes.

## Incremental Sync State

`source_sync_state` tracks per `(tenant_id, source_type, external_ref)` cursor state:

- `last_seen_modified_at`
- `last_seen_checksum`
- `last_synced_at`
- `last_status`
- `last_error_code`, `last_error_message`

Decision rule:
- no state -> fetch
- newer `last_modified` -> fetch
- changed checksum hint -> fetch
- else skip

This keeps re-runs idempotent and deterministic for identical snapshots.


## Confluence page connector

Confluence pages are synced with paging-safe two-step fetch:
1. list page descriptors from search endpoint without body expansion;
2. fetch each page body by id with configured representation (`storage`/`view`) and normalize HTML to markdown.
