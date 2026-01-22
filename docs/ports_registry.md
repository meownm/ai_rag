# Ports Registry

## Rules
- Ports are allocated in blocks of 100 per logical group.
- Every service reads ports from `.env`, and code defaults match the allocated port.
- New service types get a new range.

## Allocations

| Range | Group | Service | Port | Notes |
|------:|-------|---------|-----:|------|
| 5400-5499 | Infra | PostgreSQL | 5432 | Standard local |
| 5400-5499 | Infra | PGHero | 8081 | Exposed as web UI |
| 5400-5499 | Infra | MinIO API | 9000 | S3 endpoint |
| 5400-5499 | Infra | MinIO Console | 9001 | Admin console |

## Reserved (planned)
| Range | Group | Notes |
|------:|-------|------|
| 5500-5599 | Core APIs | document-registry, search-api, rag-api |
| 5600-5699 | Workers | embedding-worker, ingestion-worker |
| 5700-5799 | Interfaces | web-ui, telegram-miniapp backend |
| 5800-5899 | Bots | telegram bot |
