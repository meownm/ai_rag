# rag-platform

Локальный контур для RAG-платформы (Docker Desktop). Цель: нулевой ручной старт.

## Быстрый старт

1. Скопировать `.env.example` в `.env` и при необходимости поменять пароли.
2. Запуск одной командой:

```bat
infra\deploy_docker_desktop.bat
```

## Ссылки (по умолчанию)

- gateway-api: http://localhost:6103/docs
- ingest-service: http://localhost:6102/docs
- search-api: http://localhost:6101/docs
- admin-api: http://localhost:6104/docs
- Grafana: http://localhost:5602
- Prometheus: http://localhost:5601
- pgAdmin: http://localhost:5701
- Adminer: http://localhost:5702
- pgHero: http://localhost:5703
- MinIO Console: http://localhost:5704
- MinIO API: http://localhost:5705
