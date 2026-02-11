# Ingestion contract: markdown-only pipeline

## Scope

This repository's ingestion runtime accepts **markdown text** emitted by crawler adapters (Confluence and File Catalog source adapters).

- Input unit: `SourceItem` with `markdown` content.
- Normalization/chunking/indexing are performed over normalized markdown.
- No PDF/DOCX/byte-stream conversion is executed at runtime in this repo.

## Current runtime behavior

1. Crawlers return `SourceItem` objects.
2. Markdown is normalized with structure-safe rules (line endings normalized, code fences preserved, indentation preserved).
3. Source rows are upserted by `(tenant_id, source_type, external_ref)`.
4. Source versions are deduplicated by `(source_id, checksum)`.
5. Documents/chunks are created only for a new source version.
6. Existing version re-ingest reuses existing `source_version_id`, document/chunks, and performs indexing upsert only.

## Future extension hook (not wired)

The codebase includes a forward-compatible protocol and stub for byte ingestion:

- `FileByteIngestor` protocol (contract for future bytes -> `SourceItem` conversion).
- `StubFileByteIngestor` implementation that raises `NotImplementedError` by design.

This hook exists for future integration and currently has **no runtime effect**.
