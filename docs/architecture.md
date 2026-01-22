# Architecture

EPIC-01: базовая инфраструктура + минимальный рабочий контур сервисов.

Компоненты:
- PostgreSQL + pgvector + pg_trgm + unaccent
- MinIO
- Redis
- Prometheus + Grafana + Loki/Promtail
- pgAdmin + Adminer + pgHero
- 4 сервиса: gateway-api, ingest-service, search-api, admin-api

Запуск: `infra\deploy_docker_desktop.bat`.
