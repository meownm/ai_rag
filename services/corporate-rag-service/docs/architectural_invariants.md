# Architectural Invariants (Mandatory Non-Regression Constraints)

Version: 1.0.0  
Status: Mandatory  
Last Updated: 2026-02-12

These invariants are frozen constraints for `corporate-rag-service`.
Any change violating these constraints is a **release blocker** unless explicitly superseded by a new approved governance EPIC.

## Invariants

1. **Source versions immutable**  
   Ingested source snapshots and version identifiers must be immutable once recorded.

2. **Tombstone only after authoritative listing**  
   Deletions/tombstones are allowed only after authoritative source listing confirms removal.

3. **Deterministic retrieval**  
   Retrieval/ranking behavior for stable inputs must remain deterministic within configured tolerance.

4. **Strict token budget**  
   Context assembly and downstream LLM requests must enforce configured token limits.

5. **Citation grounding**  
   Generated answers must ground claims in retrievable cited chunks/documents.

6. **Tenant isolation**  
   No cross-tenant leakage is permitted in retrieval, context, storage, or logs.

## Enforcement

- These invariants must be reviewed in Architecture Review and Release Gate.
- The release checklist in `docs/release_gate_template.md` must explicitly reference this document.
- Regressions against invariants must produce NO-GO until mitigated.
