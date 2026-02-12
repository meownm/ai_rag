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
- List paragraphs are emitted with markdown list markers.
- Tables remain in-place instead of being appended at document end.

### PDF

- Extraction uses `pdfplumber` and preserves paragraph boundaries.
- Page markers are always emitted (`<!-- page:N -->`).
- Basic tables are converted to markdown tables when at least two rows are detected.

## Windows Scripts

- `run_local.bat` reads `RAG_SERVICE_PORT` from `.env`, sets window title, prints Swagger URL, and pauses on error.
- `deploy_docker_desktop.bat` reads `RAG_SERVICE_PORT` from `.env`, avoids hardcoded port assumptions, prints Swagger URL, and pauses on error.
