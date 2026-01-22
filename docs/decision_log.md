# Decision Log

## Decisions status enum
- `accepted`
- `superseded`
- `rejected`

## Decisions

### D-001 — Epic-first execution discipline
- Date: 2026-01-22
- Status: accepted
- Decision: work proceeds in strict epic order. New epic starts only via the command "начинай новый эпик". Any cross-epic work is stopped and redirected to the correct epic boundary.

### D-002 — Local infrastructure baseline
- Date: 2026-01-22
- Status: accepted
- Decision: local closed test contour uses Docker Desktop + PostgreSQL + pgvector + MinIO. PGHero is included for DB visibility.

### D-003 — Observability early
- Date: 2026-01-22
- Status: accepted
- Decision: request_id and structured JSON logging are mandatory and introduced before business logic.

### D-004 — Access model
- Date: 2026-01-22
- Status: accepted
- Decision: global admin + organizations with roles: org_admin, editor, reader.

### D-005 — Ingestion-first before embeddings/LLM
- Date: 2026-01-22
- Status: accepted
- Decision: ingestion and reproducible text extraction are built before embeddings, search ranking tuning, or RAG generation.

### D-006 — Hybrid search
- Date: 2026-01-22
- Status: accepted
- Decision: full-text baseline first, then semantic and hybrid blending with explainability.

### D-007 — LLM as draft generator only
- Date: 2026-01-22
- Status: accepted
- Decision: LLM outputs are structured (JSON/YAML) and validated; LLM is not a source of truth and has no direct DB access.
