# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to Semantic Versioning principles for release notes.

## [Unreleased]

### Added
- Formal development governance review chain documented in `docs/development_governance.md`.
- Mandatory production risk matrix artifact in `docs/production_risk_matrix.md`.
- Formal release gate template and simulation documents:
  - `docs/release_gate_template.md`
  - `docs/release_gate_simulation_epic_development_governance.md`
- Architectural invariants document in `docs/architectural_invariants.md`.
- Governance and release-gate unit tests for documentation and decision rules.
- Observability required-event integration tests with schema compliance checks.
- Strengthened governance validation tests: stop-point order checks, Open-Risk P0 guard, and release simulation SHA validation.
- Refined integration tests so non-dependent negative/shape scenarios run even when optional dependencies are unavailable.

### Changed
- Changelog governance: every merged EPIC now requires a changelog update in this file.

### Fixed
- N/A

### Removed
- N/A

### Security
- Reinforced governance controls by enforcing P0 release blocking and mandatory tenant-isolation invariant checks.

## [1.0.0] - 2026-02-12

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

### Changed
- N/A

### Fixed
- N/A

### Removed
- N/A

### Security
- N/A
