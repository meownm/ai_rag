# EPIC-7 Pipeline Trace

## Stop-point execution order

1. **REL-1 Production Docker build**
   - Updated Dockerfile to multi-stage production image.
   - Added clean image practices (apt cache cleanup, minimal runtime packages, non-root user).
   - Added `docker-entrypoint.sh` env validation.
   - Tests:
     - `tests/unit/test_release_docker_assets.py`
     - `tests/integration/test_docker_entrypoint_validation_integration.py`

2. **REL-2 Install scripts**
   - Hardened `install.bat` and `deploy_docker_desktop.bat` with `pause-on-error` flow.
   - Added script checks in `tests/unit/test_windows_release_scripts.py`.

3. **REL-3 Documentation**
   - Added release architecture, pipeline trace, observability, and security docs.

4. **REL-4 Versioning**
   - Added changelog and repository tag `1.0.0`.


## Discovery stage execution trace (`codebase-cartographer`)

### Stage scope
- Executed **only** YAML stage `discovery`.
- Scope limited to architecture/pipeline documentation baseline and hotspot identification.

### Call graph (service-level)
1. `frontend` page action (`/query`, `/ingestion`, `/diagnostics`) -> HTTP API client.
2. `corporate-rag-service` route handlers:
   - query flow -> sanitize/rate-limit -> embedding request -> retrieval (lexical+vector) -> rerank -> context expansion/budget -> LLM generation -> anti-hallucination verification -> response trace/logging.
   - ingestion flow -> connector registry -> source fetch -> normalization/chunking -> DB persistence + storage artifacts.
3. `corporate-rag-service` external calls:
   - `EmbeddingsClient` -> `embeddings-service /v1/embeddings`.
   - `OllamaClient` -> model generation endpoint.
4. `embeddings-service` route -> encoder registry -> vector generation -> dimension validation -> typed response.

### Stage outputs
- `module_map`: recorded in `docs/architecture.md`.
- `call_graph`: recorded in this document.
- `risk_hotspots`: recorded in `docs/architecture.md`.
