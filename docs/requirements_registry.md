# Requirements Registry

## Status enum
- `planned`
- `in_progress`
- `done`
- `rejected`

## Traceability rules
- Each requirement has an ID.
- Each requirement must reference:
  - decision(s) in `docs/decision_log.md` (if any)
  - implementation location(s) (path/module/service)
- Status may only be changed after real integration.

## Registry

| ID | Requirement | Epic | Priority | Status | Decisions | Implementation |
|---:|-------------|------|----------|--------|-----------|----------------|
| R-001 | Local closed test contour deployment via Docker Desktop | EPIC-1 | P0 | planned | D-001 | infra/docker-compose.yml |
| R-002 | PostgreSQL with pgvector | EPIC-1 | P0 | planned | D-002 | infra/docker-compose.yml |
| R-003 | Object storage via MinIO | EPIC-1 | P0 | planned | D-002 | infra/docker-compose.yml |
| R-004 | Observability: JSON logs + request_id | EPIC-2 | P0 | planned | D-003 | (future) |
| R-005 | Access model: global admin + org roles | EPIC-3 | P0 | planned | D-004 | (future) |
| R-006 | Ingestion: PDF/DOCX/DOC/TXT | EPIC-4 | P0 | planned | D-005 | (future) |
| R-007 | Hybrid search: FTS + vector | EPIC-6/7 | P0 | planned | D-006 | (future) |
| R-008 | RAG answers with strict structured output | EPIC-8 | P0 | planned | D-007 | (future) |
| R-009 | Telegram bot interface | EPIC-9.1 | P1 | planned | - | (future) |
| R-010 | Web UI interface | EPIC-9.2 | P1 | planned | - | (future) |
