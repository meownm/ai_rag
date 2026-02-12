# Architectural Invariants (Mandatory Non-Regression Constraints)

Version: 1.1.0  
Status: Mandatory  
Last Updated: 2026-02-12 (EPIC-INTEGRITY-HARDENING)

These invariants are frozen constraints for `corporate-rag-service`.
Any change violating these constraints is a **release blocker** unless explicitly superseded by a new approved governance EPIC.

## Invariants

1. **Source versions immutable**  
   Ingested source snapshots and version identifiers must be immutable once recorded, with object keys scoped as `tenant_id/source_id/source_version_id/*` and overwrite prevention at storage write time.

2. **Tombstone only after authoritative listing**  
   Deletions/tombstones are allowed only when connector listing explicitly reports `listing_complete=true`; if listing is truncated/incomplete, tombstones are skipped and structured warning telemetry `event_type=sync.tombstone.skipped` with `reason=listing_not_authoritative` is emitted.

3. **Deterministic retrieval**  
   Retrieval/ranking behavior for stable inputs must remain deterministic with strict tie-break ordering: `(final_score DESC, source_preference DESC, chunk_id ASC)` after deduplication.

4. **Strict token budget**  
   Context assembly and downstream LLM requests must enforce configured token limits, re-checking assembled prompt size against `LLM_NUM_CTX - TOKEN_BUDGET_SAFETY_MARGIN` and hard-failing on overflow.

5. **Citation grounding**  
   Generated answers must ground claims in retrievable cited chunks/documents; model-provided citations outside retrieved allowlist are stripped.

6. **Tenant isolation**  
   No cross-tenant leakage is permitted in retrieval, context, storage, or logs.

## Enforcement

- These invariants must be reviewed in Architecture Review and Release Gate.
- The release checklist in `docs/release_gate_template.md` must explicitly reference this document.
- Regressions against invariants must produce NO-GO until mitigated.
- CI must execute integrity regression tests that explicitly validate these invariants.
