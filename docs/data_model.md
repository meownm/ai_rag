# Data model (логическая модель)

EPIC-01 фиксирует только минимальную модель данных для FTS-only поиска.

## Схемы

- `app` — прикладные данные
- `logs` — зарезервировано под логи сервисов (следующие эпики)

## Таблица app.documents

Назначение: хранение нормализованного текста документов и подготовка к FTS запросам.

Поля:

- `document_id` (uuid, PK) — идентификатор документа
- `source_type` (text, NOT NULL) — источник (например: folder, upload, api)
- `source_ref` (text, NULL) — ссылка/путь/ключ объекта
- `title` (text, NULL) — название
- `language` (text, NULL) — язык (опционально)
- `content_text` (text, NOT NULL) — полный текст
- `content_tsv` (tsvector, STORED GENERATED) — вычисляемый tsvector для FTS (конфигурация `simple` + `unaccent`)
- `embedding` (vector(1536), NULL) — зарезервировано, в EPIC-01 не используется (оставлено под будущую семантику)
- `created_at` (timestamptz) — дата создания
- `updated_at` (timestamptz, NULL) — дата обновления

Индексы:

- `idx_documents_tsv` — GIN по `content_tsv` (FTS)
- `idx_documents_trgm` — GIN trigram по `content_text` (похожесть/опечатки)

## Трассируемость к реализации

DDL находится в миграциях:

- `infra/docker/postgres/migrations/010_documents.sql`
- `infra/docker/postgres/migrations/011_documents_indexes.sql`
