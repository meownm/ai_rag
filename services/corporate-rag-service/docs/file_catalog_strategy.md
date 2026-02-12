# File Catalog Strategy

## FCS-SP1 Local descriptor generation

- Walk root via `os.walk` (recursive) or top-level iterator.
- Normalize relative paths to POSIX form for deterministic `external_ref = fs:<rel_path>`.
- Apply case-insensitive extension filter.
- Enforce max size in descriptor stage (oversized files are skipped with `F-FILE-TOO-LARGE`).
- Enforce root boundary and reject symlink/path traversal escapes (`F-SEC-*`).
- Sort descriptors by `external_ref` and cap by `CONNECTOR_SYNC_MAX_ITEMS_PER_RUN`.


## FCS-SP2 S3 descriptor generation

- Uses `list_objects_v2` pagination with continuation token.
- Filters by configured prefix and extension set.
- Skips oversized objects (`O-OBJECT-TOO-LARGE`).
- Uses deterministic `external_ref = s3:<bucket>:<key>`.
- Uses safe single-part ETag as checksum hint when applicable.
- Sorts descriptors by key for deterministic ordering.


## FCS-SP3 Incremental decision

- Uses deterministic `should_fetch(descriptor, state, incremental_enabled)`.
- Emits structured skip log: `event=file_catalog_skip_incremental`.
- Unchanged descriptors are skipped and do not trigger fetch/ingest.


## FCS-SP4 Fetch and convert

- Local files are read in binary mode and converted through `FileByteIngestor`.
- S3 objects are downloaded and converted through the same byte->markdown path.
- Empty markdown is rejected (`F-EMPTY-MARKDOWN`, `O-EMPTY-MARKDOWN`).
- Source item metadata includes source kind (`fs`/`s3`), path/key, size and timestamps.


## FCS-SP5 Versioning integration

- Unchanged descriptors are skipped by incremental logic, so new `source_versions` are not created.
- Changed checksum/mtime triggers fetch and creates a new source version checksum row.
- Retrieval remains on latest ingested document graph via existing pipeline behavior.


## FCS-SP6 Deleted files

- If an external_ref existed in `source_sync_state` but is absent from current descriptor list, it is marked as `last_status=deleted`.
- Vectors/content are not hard-deleted automatically.
- `FILE_CATALOG_HARD_DELETE_ENABLED` is introduced (default `false`) for future destructive cleanup workflows.


## FCS-SP7 Security and safety

- Enforces root boundary for descriptors and fetch (`F-SEC-SYMLINK-ESCAPE`).
- Rejects unresolved paths (`F-SEC-RESOLVE-FAILED`).
- Rejects path traversal indicators and logs security violations with `F-SEC*` codes.
- Applies strict max file size guardrails in descriptor and fetch stages.


## FCS-SP8 Structured regression

- Integration regression covers nested fixture layout and structure-bearing markdown extracted from docx/pdf/txt/md paths through unified ingestion.
- Verifies list/table/heading text is present in resulting chunks and re-run does not duplicate documents.


## FCS-SP9 Performance guardrails

- Emits per-run summary metrics: `files_scanned`, `files_skipped`, `files_ingested`, `total_bytes`, `total_duration`.
- Enforces max items cap from sync context and logs cap events gracefully.
- Keeps descriptor ordering deterministic under cap truncation.
