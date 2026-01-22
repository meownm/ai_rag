# EPIC-01 Review

EPIC-01 фиксирует базовую инфраструктуру локального закрытого тестового контура и FTS-only подготовку PostgreSQL для следующих эпиков (search-api, ingest, ACL, гибридный поиск).

## Роли для ревью

Технические роли:

- Lead Backend / Senior Backend Engineer
- DevOps / Platform Engineer
- SRE / On-call Engineer
- DBA / Data Engineer
- QA (smoke + негативные сценарии)

Документация и требования:

- System Analyst
- Solution Architect
- Tech Writer

## Объём EPIC-01

В EPIC-01 считаем «готовым» следующий набор:

1. One-click развёртывание инфраструктуры на Docker Desktop.
2. Автогенерация `.env` из `.env.example`.
3. Автоприменение миграций и автосоздание DB-ролей и grants.
4. Готовность БД для FTS-only: tsvector + GIN + trigram.
5. Базовая наблюдаемость (Prometheus, Grafana, Loki, Promtail) и админ-инструменты (pgAdmin, Adminer, pgHero).

В EPIC-01 нет API-сервисов (они зарезервированы портами и документацией).

## Результаты ревью по ролям

### Lead Backend / Senior Backend Engineer

- Границы эпика соблюдены: нет незавершённых API-слоёв, инфраструктура не зависит от приложения.
- Схема `app.documents` подходит для FTS-only и не навязывает интерфейсы будущих сервисов.
- `content_tsv` вычисляемая STORED-колонка снижает нагрузку на запросы и упрощает API.

Замечания:

- В `.env.example` есть параметры для гибрида (веса). Для EPIC-01 они должны быть явно «выключены». Это зафиксировано в DEC-0004 (векторный вес = 0).

### DBA / Data Engineer

- Миграции идемпотентны (`IF NOT EXISTS`) и применимы повторно.
- Есть отдельные схемы `app` и `logs`, что упрощает разграничение доступа.
- Индексы:
  - GIN по `content_tsv` — для FTS.
  - GIN trigram по `content_text` — для «похожести»/подстрок.

Замечания:

- `vector` extension и `embedding` колонка присутствуют как задел. Для EPIC-01 не используются, риск минимальный. Важно не вводить API-контракты под векторный поиск до отдельного решения.

### DevOps / Platform Engineer

- Docker Compose стек самодостаточен и поднимается из `infra/docker/docker-compose.yml`.
- Разделение конфигурации:
  - переменные в `.env`;
  - конфиги Grafana/Prometheus/Promtail в репозитории.

Проверка требований «минимум ручных действий»:

- `infra\install.bat` автоматически создаёт `.env`.
- `infra\start.bat` поднимает стек и запускает `db-migrator` + `minio-init`.

Замечания:

- Promtail читает docker-логи через `/var/lib/docker/containers`. Это нормально для Linux-контейнеров Docker Desktop, но при нетиповых настройках может понадобиться уточнение в docs/observability.md.

### SRE / On-call Engineer

- Есть smoke-тест, который проверяет критическую готовность БД и базовые health/readiness для MinIO, Prometheus и Grafana.
- Есть скрипты `status` и `stop/reset` с понятной моделью.

Замечания:

- `reset-no-confirm` — осознанно опасная операция. В docs/failure_scenarios.md стоит держать явный сценарий восстановления (включая пересоздание volumes).

### System Analyst / Solution Architect

- Трассировка пайплайна (docs/pipeline_trace.md) соответствует реализациям скриптов и миграций.
- Реестр портов с диапазонами по 100 соблюдён, зарезервированы порты будущих сервисов.
- Decision log фиксирует принципиальные решения и границы эпика.

Замечания:

- Для следующих эпиков желательно зафиксировать требования к доменной модели (организации/права) до реализации search-api.

### QA (smoke + негативные сценарии)

Покрыто:

- Smoke: поднятие контейнеров, наличие таблицы `app.documents`, readiness MinIO, readiness Prometheus, health Grafana.

Нужно на следующий эпик:

- Негативные сценарии:
  - отсутствует `.env.example`;
  - Docker Desktop выключен;
  - заняты порты;
  - битые volume (неконсистентность Postgres data-dir).

## Итог

EPIC-01 можно считать завершённым как инфраструктурный «фундамент» для локального тестового контура и FTS-only.

## Рекомендации на следующий эпик (FTS-only)

1. `search-api` (FastAPI): `/health`, `/search`, Swagger, подключение к Postgres по `POSTGRES_DSN`, обязательный `request_id`.
2. `ingest-service` (минимум: загрузка текста в `app.documents`).
3. Логирование API-запросов в `logs.api_requests` в режиме `LOG_DATA_MODE=plain|masked` по глобальному стандарту.