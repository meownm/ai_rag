# Release Gate Template

Version: 1.0.0  
Status: Mandatory  
Last Updated: 2026-02-12

## Release Candidate Metadata

- EPIC ID:
- Release Candidate:
- Date:
- Release Authority Agent:
- Commit SHA:

## Mandatory Checklist

- [ ] All **P0** risks are closed in `docs/production_risk_matrix.md`.
- [ ] Schema is consistent and validated.
- [ ] Retrieval behavior is deterministic for golden queries.
- [ ] Token budget constraints are enforced.
- [ ] Versioning is correct for docs and release artifacts.
- [ ] Logs are structured JSON.
- [ ] Audit event is present for the release decision.
- [ ] Architectural invariants are re-validated against `docs/architectural_invariants.md`.
- [ ] Integrity regression suite for architectural invariants passed in CI.

## Review Chain Evidence

- Design Review verdict:
- Regression Review verdict:
- Architecture Review verdict:
- Quality Review verdict:
- Observability Review verdict:
- Production Risk Matrix update reference:

## Decision Outcomes

Choose one:

- **GO** — all mandatory checks pass with acceptable residual risk.
- **GO WITH LIMITATIONS** — non-critical risks remain; explicit operational limitations and mitigation dates required.
- **NO-GO** — one or more release blockers remain (including any open P0 risk).

## Decision Record

- Outcome:
- Rationale:
- Limitations (if any):
- Required follow-up actions:
- Approved by:
- Timestamp:
