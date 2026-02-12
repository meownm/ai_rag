# EPIC-7 Security and Access

## Container runtime hardening

For `corporate-rag-service` release image:

- Runtime container executes as non-root user `appuser`.
- Image includes only required runtime packages (`libpq5`, `curl`).
- Build tooling remains in builder stage and is not required at runtime.

## Configuration safety

The runtime entrypoint blocks startup when critical settings are absent or malformed:

- Invalid `APP_ENV` values are rejected.
- Empty `DATABASE_URL` is rejected.
- Empty `EMBEDDINGS_SERVICE_URL` is rejected.

This fail-fast approach prevents partial startup in insecure or undefined configurations.
