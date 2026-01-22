# Configuration

## Основной принцип

Вся конфигурация берётся из `.env` в корне репозитория. Шаблон: `.env.example`.

## Обязательные параметры

- `PROJECT_NAME` — префикс имён контейнеров
- `POSTGRES_*` — параметры PostgreSQL и роли
- `MINIO_*` — параметры MinIO
- `PROMETHEUS_HOST_PORT`, `GRAFANA_HOST_PORT`, `LOKI_HOST_PORT` — наблюдаемость
- `PGADMIN_HOST_PORT`, `ADMINER_HOST_PORT`, `PGHERO_HOST_PORT` — админ-инструменты

## Роли БД

Роли создаются и права назначаются автоматически мигратором:

- `POSTGRES_APP_USER` — чтение/запись в `app`
- `POSTGRES_READONLY_USER` — только чтение из `app`

Пароли задаются в `.env`.
