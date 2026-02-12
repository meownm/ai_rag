# Changelog

## 1.0.0 - 2026-02-12

### Added
- Production-ready multi-stage Docker build for `corporate-rag-service` with reduced runtime image content.
- Runtime entrypoint validation script (`docker-entrypoint.sh`) that fails fast for invalid `APP_ENV` and missing required env vars.
- Hardened Windows scripts (`install.bat`, `deploy_docker_desktop.bat`) with enforced pause-on-error flow.
- EPIC-7 release documentation in repository docs:
  - `docs/architecture.md`
  - `docs/pipeline_trace.md`
  - `docs/observability.md`
  - `docs/security_and_access.md`
- Automated release artifact tests for Docker/build assets, entrypoint env validation, and Windows deploy scripts.
