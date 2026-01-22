# Pipeline Trace

Документ фиксирует шаги пайплайна на уровне EPIC-01.

## 1. Развёртывание инфраструктуры

1. `infra\install.bat` создаёт `.env` из `.env.example` (если отсутствует).
2. `infra\start.bat` поднимает Docker Compose стек.
3. `db-migrator` применяет миграции:
   - `public.schema_migrations`
   - `CREATE EXTENSION` (pg_trgm, unaccent, vector)
   - `CREATE SCHEMA` (app, logs)
   - `CREATE TABLE app.documents` с вычисляемым `tsvector`
   - индексы GIN по `tsvector` и trigram по `content_text`
   - создание ролей и grants
4. `minio-init` создаёт бакеты.

## 2. Подготовка к FTS-only поиску

Таблица `app.documents` и индексы позволяют реализовать FTS-only поиск в следующем эпике через запросы вида:

- `WHERE content_tsv @@ plainto_tsquery('simple', unaccent(:q))`
- `ORDER BY ts_rank_cd(content_tsv, plainto_tsquery(...)) DESC`

Триграм-индекс предназначен для:
- поиска по подстроке
- опечаток и похожести через `similarity()` и `%` оператор.

## 3. Заглушки следующих эпиков

`services/` и API порты в `.env.example` зарезервированы, но не используются в EPIC-01.
