# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to Semantic Versioning principles for release notes.

## [Unreleased]

### Added
- INT-SP3 follow-up: aligned ORM `ChunkVectors` model with DB/UPSERT contract by declaring `uq_chunk_vectors_tenant_chunk` composite unique constraint.
- INT-SP3: Aligned `chunk_vectors` UPSERT conflict target with schema (`tenant_id, chunk_id`) and added guard migration for `updated_at` + composite unique index.
- Added integration schema assertions for `chunk_vectors.updated_at` default/NOT NULL and UPSERT update-path behavior on fresh migrated DB.
- INT-SP2: Enforced immutable versioned storage writes under `tenant_id/source_id/source_version_id/raw.bin` with mandatory immutable-write APIs.
- Added immutable storage integration tests for modified vs identical re-ingest content and no-duplicate-version guarantees.
- Added storage invariant tests that manual overwrite of an existing immutable key fails with controlled error.
- Follow-up review: documented versioned markdown/artifact S3 paths in `docs/pipeline_trace.md` and added regression test coverage for this contract.
- Added negative ingestion test to enforce controlled failure when immutable storage methods are unavailable.
- INT-SP1: Tombstone safety hardening in sync pipeline: tombstones are skipped when connector listing is non-authoritative and structured event `sync.tombstone.skipped` is emitted.
- Added integration tests for tombstone safety (non-authoritative listing negative scenario + authoritative listing positive scenario).
- Added roadmap document `docs/production_grade_roadmap_v1.md` to lock execution order from Governance Foundation through Production Gate.
- Updated governance documentation and release-gate artifacts to include the mandatory Implementation stage in review-chain evidence.
- Added Phase 0 governance validation tests (unit + integration), including positive and negative guardrail scenarios for release blockers and non-regression constraints.
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
