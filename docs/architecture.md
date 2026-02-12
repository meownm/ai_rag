# EPIC-7 Release Architecture

## REL-1: Production Docker build

`services/corporate-rag-service` now ships with a multi-stage Docker image:

1. **builder stage** installs Poetry dependencies and assembles runtime artifacts.
2. **runtime stage** copies only built artifacts, runs as a non-root `appuser`, and keeps a small final footprint.
3. `docker-entrypoint.sh` validates mandatory runtime environment variables before launching Uvicorn.

## Runtime validation contract

The container enforces:

- `APP_ENV` must be one of `production|staging|development`.
- `DATABASE_URL` must be set.
- `EMBEDDINGS_SERVICE_URL` must be set.

If validation fails, startup stops with a non-zero exit code.
