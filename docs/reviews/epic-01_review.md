# EPIC-01 Review

## Роли для ревью

- Lead Backend / Senior Backend Engineer
- DevOps / Platform Engineer
- SRE / On-call Engineer
- System Analyst
- Solution Architect
- Tech Writer

## Итоги ревью

### 1) Корректность и завершённость EPIC-01
- Docker Compose стек поднимается одной командой, миграции применяются автоматически.
- Схема БД готова для FTS-only поиска (tsvector + GIN, trigram индекс).
- Пользователи БД создаются автоматически и получают права.

### 2) Риски
- `reset-no-confirm` удаляет volumes. Требуется дисциплина использования.
- Пароли в `.env` не должны содержать кавычки и переносы строк (ограничение migrator).
- В `.env.example` зарезервированы порты сервисов будущих эпиков, но сервисов пока нет. Это зафиксировано в документации.

### 3) Проверки
- `infra\smoke_test.bat` проверяет PostgreSQL, наличие таблицы `app.documents`, readiness MinIO/Prometheus и health Grafana.
- `infra\status.bat` печатает доступные URL.

## Рекомендации на следующий эпик (FTS-only)
- добавить минимальный `search-api` (FastAPI) с эндпоинтом `/search` и `/health`, подключением к Postgres по `POSTGRES_DSN`, и Swagger.
- добавить ingest (минимум: загрузка текста) в `app.documents`.
- добавить admin-api: CRUD организаций/пользователей и ACL (если требуется для FTS-only).
