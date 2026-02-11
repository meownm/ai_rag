# Code Review: AI RAG Platform

**Дата:** 2026-02-11
**Ревизия:** main (4fc5810)
**Ревьюер:** Claude Code

---

## Резюме

Проект представляет собой enterprise-grade мультитенантную RAG-платформу с микросервисной архитектурой (backend на FastAPI, embeddings-сервис, React-фронтенд). Архитектура продуманная, код в целом хорошо структурирован. Ниже перечислены найденные проблемы по категориям: критические, важные и рекомендации.

---

## CRITICAL - Критические проблемы

### 1. Отсутствие аутентификации и авторизации на API-эндпоинтах

**Файлы:** `services/corporate-rag-service/app/api/routes.py`, `services/embeddings-service/app/api/routes.py`

Все эндпоинты (`/v1/query`, `/v1/ingest/sources/sync`, `/v1/jobs/{job_id}`) полностью открыты. Нет middleware для проверки JWT/API-ключей, нет проверки принадлежности tenant_id к текущему пользователю. Любой клиент может:
- Выполнять запросы от имени любого tenant_id
- Запускать ingestion для любого тенанта
- Просматривать статус любых jobs

На фронтенде `AuthProvider` (`frontend/src/providers/AuthProvider.tsx:7`) возвращает hardcoded `userId: 'local-user'`, а `TenantProvider` (`frontend/src/providers/TenantProvider.tsx:8`) содержит hardcoded UUID. Эти заглушки пригодны только для разработки.

**Рекомендация:** Реализовать middleware аутентификации (JWT/OAuth2) и проверку `tenant_id` через binding текущего пользователя. Модели `Users`, `UserGroupMemberships`, `TenantGroupBindings` уже определены, но нигде не используются в runtime.

### 2. Hardcoded credentials в дефолтных значениях конфигурации

**Файл:** `services/corporate-rag-service/app/core/config.py:14-23`

```python
DB_PASSWORD: str = "postgres"
S3_ACCESS_KEY: str = "minio"
S3_SECRET_KEY: str = "minio123"
```

Дефолтные значения содержат реальные credentials. Если `.env` файл отсутствует или неполный, сервис запустится с этими паролями. Это также создаёт риск случайного коммита `.env` файла.

**Рекомендация:** Убрать дефолтные значения для секретов и использовать `pydantic_settings` валидацию для обязательных полей. При отсутствии переменных сервис должен падать при старте, а не работать с дефолтными паролями.

### 3. SQL Injection через `_upsert_fts_for_chunks`

**Файл:** `services/corporate-rag-service/app/services/ingestion.py:810`

```python
f"""
INSERT INTO chunk_fts (tenant_id, chunk_id, fts_doc, updated_at)
SELECT c.tenant_id,
       c.chunk_id,
       ({weighted_fts_expression()}),
       now()
FROM chunks c
...
"""
```

Функция `weighted_fts_expression()` из `app/cli/fts_rebuild.py` вставляется через f-string в SQL-запрос. Хотя сейчас она возвращает статическую строку, любое изменение этой функции, принимающее внешний ввод, создаст вектор SQL-инъекции. Кроме того, параметр `chunk_ids` передаётся через `:chunk_ids` с `ANY()`, что может не работать корректно для всех драйверов.

**Рекомендация:** Вынести FTS-выражение как SQL-литерал через `text()` с параметризацией, либо зафиксировать его как константу.

---

## HIGH - Важные проблемы

### 4. Эндпоинт `/v1/query` - гигантская функция без транзакционного контроля

**Файл:** `services/corporate-rag-service/app/api/routes.py:253-565`

Функция `post_query` занимает ~310 строк и содержит:
- Conversation management
- Query rewriting через LLM
- Summarization
- Clarification loop
- Embedding, retrieval, reranking
- LLM generation
- Anti-hallucination verification
- Logging и tracing

Проблемы:
- **Нет явного управления транзакциями.** Множественные `db.commit()` вызываются внутри репозиториев (каждый `create_turn`, `create_query_resolution`, `touch_conversation` коммитит отдельно). При ошибке между коммитами данные останутся в неконсистентном состоянии.
- **Нет `db.rollback()` при исключениях.** Session не откатывается при ошибках между коммитами.
- **Нарушение SRP.** Бизнес-логика, оркестрация, I/O и логирование смешаны в одной функции.

**Рекомендация:** Вынести оркестрацию в service-layer. Использовать единый commit в конце успешной транзакции. Рассмотреть паттерн Unit of Work.

### 5. `datetime.utcnow()` deprecated

**Файл:** `services/corporate-rag-service/app/models/models.py:97, 226, 227, 239, 256, 277, 291`

```python
started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
```

`datetime.utcnow()` deprecated в Python 3.12+ (DeprecationWarning). Он возвращает naive datetime без tzinfo, что конфликтует с `DateTime(timezone=True)` в колонке.

**Рекомендация:** Заменить на `default=lambda: datetime.now(timezone.utc)` или использовать `server_default=func.now()`.

### 6. Отсутствие rate limiting и ограничения размера входных данных

**Файл:** `services/corporate-rag-service/app/schemas/api.py:15-19`

```python
class QueryRequest(BaseModel):
    tenant_id: UUID
    query: str          # Нет ограничения длины
    citations: bool | None = None
    top_k: int = Field(default=10, ge=1, le=50)
```

Поле `query` не имеет ограничения по длине. Клиент может отправить мегабайты текста, которые будут переданы в embedding-сервис, LLM и full-text search. Аналогично, `SourceSyncRequest.source_types` не валидируется.

**Рекомендация:** Добавить `max_length` на `query` (например, 10000 символов). Добавить `Literal` или `Enum` валидацию для `source_types`. Рассмотреть rate limiting через middleware.

### 7. Синхронная обработка ingestion в HTTP-запросе

**Файл:** `services/corporate-rag-service/app/api/routes.py:220-235`

```python
@router.post("/v1/ingest/sources/sync", ...)
def start_source_sync(payload: SourceSyncRequest, db: Session = Depends(get_db)):
    ...
    ingest_sources_sync(db, payload.tenant_id, payload.source_types)
    ...
```

Несмотря на status code 202 (Accepted), обработка выполняется синхронно. Для больших объёмов данных это приведёт к таймаутам HTTP-соединения. Embedding-батчи также обрабатываются синхронно с `time.sleep()` в retry-логике.

**Рекомендация:** Реализовать фоновую обработку через Celery, asyncio background tasks, или очередь сообщений. Вернуть job_id и обрабатывать asynchronously.

### 8. Потенциальная утечка embedding-векторов через `_row_to_candidate`

**Файл:** `services/corporate-rag-service/app/db/repositories.py:259`

```python
"embedding": list(vector.embedding),
```

Полные embedding-векторы (1024 float) загружаются для каждого кандидата и передаются через весь pipeline. Это:
- Увеличивает memory footprint (1024 * 8 bytes * N кандидатов)
- Потенциально утекает в API response через trace/logging
- Пересчитывается в `retrieval.py:vector_score()` хотя скор уже был вычислен в SQL

**Рекомендация:** Не загружать embedding в candidate dict, если vector score уже получен из PostgreSQL. Если нужен для reranking — загружать отдельно.

### 9. Двойное вычисление `hybrid_rank`

**Файл:** `services/corporate-rag-service/app/api/routes.py:415-427`

```python
ranked, timers = hybrid_rank(query, candidates, query_embedding, ...)
reranked, t_rerank = get_reranker().rerank(query, ranked)
ranked_final, _ = hybrid_rank(query, reranked, query_embedding, ...)
```

`hybrid_rank` вызывается дважды: до и после reranking. Первый вызов вычисляет lexical и vector scores, затем reranker пересчитывает scores, и второй вызов `hybrid_rank` снова пересчитывает lexical и vector scores (с нуля), только чтобы включить новый rerank_score в финальную формулу.

**Рекомендация:** После reranking достаточно пересчитать `final_score` с учётом нового `rerank_score`, без полного повторного запуска `hybrid_rank`.

### 10. `get_db()` не выполняет `rollback` при ошибках

**Файл:** `services/corporate-rag-service/app/db/session.py:15-20`

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

При исключении сессия просто закрывается без явного rollback. SQLAlchemy может откатить транзакцию при close(), но это implementation detail. Явный rollback безопаснее.

**Рекомендация:**
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

---

## MEDIUM - Проблемы среднего приоритета

### 11. Модуль `query_pipeline.py` читает env-переменные напрямую

**Файл:** `services/corporate-rag-service/app/services/query_pipeline.py:6-10`

```python
DEFAULT_TOP_K = int(getenv("DEFAULT_TOP_K", "5"))
USE_CONTEXTUAL_EXPANSION = getenv("USE_CONTEXTUAL_EXPANSION", "false").lower() == "true"
```

Дублирование конфигурации: `config.py` использует `pydantic_settings`, а `query_pipeline.py` читает `os.getenv()` напрямую. Значения могут разойтись.

**Рекомендация:** Использовать единый источник конфигурации через `settings`.

### 12. `_Fallback` класс в ingestion скрывает ошибки конфигурации

**Файл:** `services/corporate-rag-service/app/services/ingestion.py:94-118`

```python
def _load_settings():
    try:
        from app.core.config import settings
        return settings
    except Exception:
        class _Fallback:
            S3_ENDPOINT = "http://localhost:9000"
            ...
```

При невозможности загрузки settings, сервис тихо использует fallback с hardcoded значениями. Это маскирует реальные ошибки конфигурации.

**Рекомендация:** Убрать fallback. Если settings не загружаются — это критическая ошибка, которая должна быть проброшена.

### 13. `lru_cache` на singleton-сервисах в `routes.py`

**Файл:** `services/corporate-rag-service/app/api/routes.py:40-51`

```python
@lru_cache
def get_reranker() -> RerankerService:
    return RerankerService(settings.RERANKER_MODEL)
```

`lru_cache` на функции без параметров загружает ML-модели (CrossEncoder, SentenceTransformer) при первом вызове и хранит навсегда. Проблемы:
- Модель грузится lazy при первом запросе (cold start spike)
- Нет возможности переключить модель без перезапуска
- Memory leak при тестировании (кэш не сбрасывается)

**Рекомендация:** Рассмотреть инициализацию при старте приложения (lifespan event) для предсказуемого cold start.

### 14. Модель `Documents` ссылается на несуществующие колонки

**Файл:** `services/corporate-rag-service/app/models/models.py:54-62` vs `ingestion.py:553-577`

В `_insert_document` используются колонки `source_id` и `source_version_id`, но SQLAlchemy-модель `Documents` не содержит этих полей. Это означает что ORM-модель и raw SQL работают с разными представлениями таблицы.

**Рекомендация:** Привести модель `Documents` в соответствие с реальной схемой БД, добавив `source_id` и `source_version_id` поля.

### 15. Отсутствие CORS middleware

**Файл:** `services/corporate-rag-service/app/main.py`

FastAPI-приложение не настраивает CORS. Фронтенд на React (отдельный origin) не сможет обращаться к API без CORS headers в production.

**Рекомендация:** Добавить `CORSMiddleware` с настраиваемыми origins.

### 16. Embeddings-сервис: нет лимита на batch size

**Файл:** `services/embeddings-service/app/api/routes.py:33`

Эндпоинт `/v1/embeddings` принимает `payload.input` без ограничения на количество текстов. Клиент может отправить тысячи текстов в одном запросе, вызвав OOM.

**Рекомендация:** Добавить валидацию `max_items` на поле `input` в `EmbeddingsRequest`.

### 17. `_extract_json_payload` — ненадёжный парсинг JSON из LLM

**Файл:** `services/corporate-rag-service/app/api/routes.py:77-89`

```python
match = re.search(r"\{.*\}", raw, re.S)
```

Regex `\{.*\}` с `re.S` жадно захватит всё от первого `{` до последнего `}` в строке. Если LLM вернёт несколько JSON-объектов или текст с фигурными скобками, результат будет непредсказуемым.

**Рекомендация:** Использовать нежадный regex `\{.*?\}` или специализированный JSON-парсер для LLM-output (например, итерация по скобкам с подсчётом вложенности).

---

## LOW - Рекомендации

### 18. Отсутствие `ForeignKey` на `Documents.tenant_id`

**Файл:** `services/corporate-rag-service/app/models/models.py:57`

```python
tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
```

`tenant_id` в `Documents`, `Chunks`, `ChunkVectors`, `IngestJobs`, `EventLogs` и других таблицах не имеет `ForeignKey("tenants.tenant_id")`. Это означает что referential integrity на уровне БД не гарантирована.

### 19. Enums определены как tuples вместо Python Enum

**Файл:** `services/corporate-rag-service/app/models/models.py:12-37`

```python
SOURCE_TYPE = ("CONFLUENCE_PAGE", "CONFLUENCE_ATTACHMENT", "FILE_CATALOG_OBJECT")
```

Использование tuples вместо `enum.Enum` лишает IDE автокомплита, type-safety, и затрудняет валидацию.

### 20. `SearchCandidates` — таблица без tenant-фильтрации

**Файл:** `services/corporate-rag-service/app/models/models.py:103-112`

Таблица `SearchCandidates` не содержит `tenant_id`. Это потенциальная проблема для multi-tenant изоляции, если данные из разных тенантов попадут в одну выборку.

### 21. Front-end не отправляет `tenant_id` и `conversation_id`

**Файл:** `frontend/src/hooks/useQueryRag.ts`

Hooks используют hardcoded tenant из context, но conversation management (X-Conversation-Id header) не реализован на клиенте, хотя backend его поддерживает.

### 22. `_estimate_token_count` — слишком грубая оценка

**Файл:** `services/corporate-rag-service/app/api/routes.py:111-113`

```python
def _estimate_token_count(text: str) -> int:
    return max(1, int(words * 1.33)) if text.strip() else 0
```

Множитель 1.33 очень приблизителен. В `query_pipeline.py` есть `estimate_tokens()` с tiktoken-fallback, но в routes используется эта грубая версия.

### 23. Anti-hallucination: загрузка модели при каждой проверке

**Файл:** `services/corporate-rag-service/app/services/anti_hallucination.py:16-20`

`_load_sentence_transformer` кэширован через `@lru_cache`, но `_semantic_similarity` вызывает `model.encode()` для каждого предложения отдельно. При N предложений и M чанков это N*M вызовов encode. Batch encoding значительно эффективнее.

---

## Положительные стороны

1. **Tenant isolation в repositories** — все запросы в `TenantRepository` и `ConversationRepository` фильтруют по `tenant_id`.
2. **Structured error responses** — единый формат ошибок через `ErrorEnvelope`.
3. **Comprehensive audit logging** — каждый этап pipeline логируется.
4. **Feature flags** — функциональность легко включается/выключается через конфигурацию.
5. **Deterministic chunk IDs** — `stable_chunk_id()` обеспечивает идемпотентность.
6. **Idempotent ingestion** — проверка checksum и dedup source versions.
7. **Anti-hallucination layer** — верификация ответа перед возвратом.
8. **Clarification loop с лимитом** — ограничение на количество последовательных уточнений (max 2).
9. **Хорошее покрытие тестами** — 25+ тест-файлов, unit и integration.
10. **Typed frontend** — Zod-валидация API-ответов и TypeScript.

---

## Приоритизация исправлений

| Приоритет | # | Проблема | Усилие |
|-----------|---|----------|--------|
| P0 | 1 | Аутентификация и авторизация | Высокое |
| P0 | 2 | Hardcoded credentials | Низкое |
| P0 | 3 | SQL injection риск | Низкое |
| P1 | 4 | Рефакторинг post_query + транзакции | Среднее |
| P1 | 5 | datetime.utcnow deprecation | Низкое |
| P1 | 6 | Rate limiting и input validation | Среднее |
| P1 | 7 | Async ingestion | Высокое |
| P1 | 10 | Rollback в get_db() | Низкое |
| P2 | 8 | Embedding leak в candidates | Низкое |
| P2 | 9 | Двойной hybrid_rank | Низкое |
| P2 | 14 | ORM/SQL schema mismatch | Низкое |
| P2 | 15 | CORS | Низкое |
