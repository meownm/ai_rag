# Ingestion pipeline trace (as-is + prod hardening points)

## As-is flow specification

`SourceSyncRequest -> /v1/ingest/sources/sync -> ingest_jobs(queued) -> worker poll -> ingest_sources_sync -> S3 raw/md -> documents/chunks -> chunk_vectors -> chunk_fts`

### Runtime steps
1. API endpoint `/v1/ingest/sources/sync` validates `tenant_id` + `source_types` and creates `ingest_jobs` record with `job_status=queued` and `job_payload_json`.
2. Dedicated worker (`app/workers/ingest_worker.py`) polls `ingest_jobs` with `FOR UPDATE SKIP LOCKED`, flips status to `processing`, runs `ingest_sources_sync`, and marks `done/error` with `result_json` and errors.
3. `ingest_sources_sync` calls crawler adapters by source type and normalizes markdown.
4. Pipeline writes source artifacts:
   - raw source payload to `S3_BUCKET_RAW` as immutable `raw.bin` (all source types).
   - normalized markdown to `S3_BUCKET_MARKDOWN`
5. Pipeline upserts `sources`, `source_versions` (checksum), `documents`, `chunks`, `document_links/cross_links`.
6. Embedding indexing writes `chunk_vectors` using `embedding_text = "[H] {chunk_path}\n{chunk_text}"`.
7. FTS indexing writes `chunk_fts` using weighted expression.

## Known extension points and gaps

- `StubFileByteIngestor` exists as explicit legacy gap marker in `app/services/ingestion.py`.
- Default crawlers are `NoopConfluenceCrawler` / `NoopFileCatalogCrawler` (return empty lists).
- Upload flow is implemented via `/v1/ingest/files/upload` + `FileByteIngestor` for `.txt/.md/.docx/.pdf`.
- Job execution is asynchronous via dedicated worker process (no Redis, no cron).

## DB tables touched

- `ingest_jobs`: queue state, payload, execution result.
- `sources`, `source_versions`: source identity + checksumed content versions.
- `documents`, `chunks`: normalized document graph.
- `chunk_vectors`: semantic vectors and embedding mode metadata.
- `chunk_fts`: lexical index rows.
- `document_links`, `cross_links`: extracted links.

## S3 artifacts

- `s3://<raw-bucket>/<tenant>/<source>/<source_version>/raw.bin` (legacy rows keep existing URIs in DB and remain readable by URI).
- `s3://<markdown-bucket>/<tenant>/<source>/<source_version>/normalized.md`
- `s3://<markdown-bucket>/<tenant>/<source>/<source_version>/artifacts/ingestion.json`


## Unified connector flow

- `ingest_sources_sync` builds connector registry and `SyncContext`.
- Connectors list descriptors, then items are fetched descriptor-by-descriptor.
- Incremental skipping uses `source_sync_state` before fetching payload bytes/body.
- Structured summary log emitted with counters: `descriptors_listed`, `items_fetched`, `items_skipped_incremental`, `items_ingested`, `items_failed`.

- Confluence conversion strategy: `docs/confluence_html_to_markdown_strategy.md`.
