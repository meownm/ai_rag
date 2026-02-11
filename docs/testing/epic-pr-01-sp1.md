# EPIC-PR-01 SP1: Tenant Isolation Guardrails

## What changed
- Added a tenant-scoped repository helper (`TenantRepository`) for critical read/write paths used by query/job/log flows.
- Routed API ingest job creation/status updates and candidate retrieval through repository calls.
- Added an explicit tenant-safe filtering step before building citations in `/v1/query`.
- Added tests for:
  - cross-tenant leakage prevention in query citations;
  - static guard against direct ORM access to critical models in API/services.

## Validation
Run:

```bash
pytest -q tests/unit/test_tenant_isolation.py
pytest -q
```

## SP2 bootstrap
- Added `tools/drift_check.py` as CI-friendly `python -m tools.drift_check` command.
- Added `tests/unit/test_drift_check.py` with PASS and simulated FAIL scenarios.

- Extended `tools/drift_check.py` env extras allowlist for internal EPIC-08 runtime flags (conversation memory/query rewrite/clarification) to keep architecture-freeze drift checks stable without mutating frozen env contracts.
- Added unit regressions for drift allowlist behavior:
  - positive: all EPIC-08 env flags are covered by `tools/drift_check.py` allowlist;
  - negative: unknown EPIC-08-like env key still surfaces as drift (`REWRITE_UNKNOWN_FLAG`).
