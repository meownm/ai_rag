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
