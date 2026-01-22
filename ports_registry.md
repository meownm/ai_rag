# ports_registry.md

## Диапазоны (по 100)

### 5400–5499 — Core Data
- 5410: PostgreSQL (host -> container 5432)

### 5600–5699 — Observability
- 5601: Prometheus (host -> 9090)
- 5602: Grafana (host -> 3000)
- 5603: Loki (host -> 3100)

### 5700–5799 — Admin Tools
- 5701: pgAdmin (host -> 80)
- 5702: Adminer (host -> 8080)
- 5703: pgHero (host -> 8080)
- 5704: MinIO Console (host -> 9001)
- 5705: MinIO API (host -> 9000)

### 5800–5899 — Cache / Queue
- 5801: Redis (host -> 6379)

### 6100–6199 — Core API
- 6101: search-api
- 6102: ingest-service
- 6103: gateway-api
- 6104: admin-api
