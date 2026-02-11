# Infrastructure (Local / Docker Desktop)

## What is included
- **PostgreSQL 16** — основная БД + db-migrator для миграций
- **Redis 7** — кэш / очереди
- **MinIO** — S3-совместимое хранилище + minio-init для создания бакетов
- **Prometheus** — сбор метрик
- **Loki + Promtail** — агрегация логов
- **Grafana** — дашборды (метрики + логи)
- **Adminer** — веб-клиент для БД
- **PGHero** — мониторинг PostgreSQL
- **pgAdmin** — администрирование PostgreSQL

## Files
- `docker/docker-compose.yml` — основной compose-файл
- `docker/.env.example` — пример переменных окружения
- scripts:
  - `start.bat` — поднять стек + миграции + minio-init
  - `stop_all.bat` — остановить стек
  - `reset_all.bat` — остановить и удалить volumes
  - `status.bat` — статус контейнеров
  - `pull_images.bat` — обновить образы
  - `smoke_test.bat` — базовый smoke-тест
  - `install_prereqs.bat` — проверка docker / docker compose

## Usage
1. Copy `docker/.env.example` -> `docker/.env`
2. Run `start.bat`
3. Run `smoke_test.bat`
