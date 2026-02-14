# docs/requirements_registry.md

## EPIC-MODEL-01 — Multilingual Model Stack Upgrade

---

## REQ-M1 — Multilingual Embeddings Support

**Описание**  
Система должна использовать мультиязычную embedding-модель, корректно работающую с RU/EN смешанным контентом Confluence и файловых источников.

**Причина**  
Англоязычные модели создают перекос в retrieval и ухудшают recall для RU-документов.

**Обязательные параметры**
- OLLAMA_MODEL
- MAX_EMBED_BATCH_SIZE
- EMBEDDINGS_TIMEOUT_SECONDS
- EMBEDDINGS_P95_BUDGET_MS

**Требования реализации**
- Проверка наличия модели при старте
- Fail fast при отсутствии
- Логирование модели, batch size, duration
- Budget enforcement

**Acceptance Criteria**
- Retrieval для RU/EN документации демонстрирует симметричный recall
- Embedding latency логируется
- Budget configurable через env

**Статус**: Planned  
**Связь**: Retrieval layer, Anti-hallucination guard

---

## REQ-M2 — Multilingual Reranker

**Описание**  
Reranker обязан поддерживать RU/EN.

**Обязательные параметры**
- RERANKER_MODEL
- RERANKER_TOP_K
- RERANKER_P95_BUDGET_MS

**Требования реализации**
- Lazy model load
- Проверка валидности top_k
- Логирование model, candidate_count, duration_ms
- Budget enforcement

**Acceptance Criteria**
- Ranking для RU-запросов корректен
- Reranker реально влияет на порядок выдачи

**Статус**: Planned  
**Связь**: Hybrid retrieval

---

## REQ-M3 — Hybrid Retrieval Tuning

**Описание**  
Hybrid retrieval должен использовать настраиваемые глубины и весовой коэффициент.

**Новые параметры**
- LEX_TOP_K
- VEC_TOP_K
- HYBRID_ALPHA
- DEFAULT_TOP_K

**Требования реализации**
- union(lex, vec)
- final_score = alpha * vec + (1 - alpha) * lex
- alpha ∈ [0,1]
- логирование alpha

**Acceptance Criteria**
- Корректная нормализация
- Нет hardcoded значений

**Статус**: Planned  
**Связь**: BM25 layer, pgvector

---

## REQ-M4 — LLM RU/EN Stability

**Описание**  
LLM должен быть устойчив к RU регламентному языку.

**Параметры**
- LLM_MODEL
- LLM_KEEP_ALIVE
- REQUEST_TIMEOUT_SECONDS

**Требования реализации**
- Передача keep_alive в Ollama
- Таймаут configurable
- Логирование provider/model/duration

**Acceptance Criteria**
- Нет зависших сессий
- Нет hardcoded таймаутов

**Статус**: Planned

---

## REQ-M5 — Anti-Hallucination Threshold Control

**Параметры**
- MIN_SENTENCE_SIMILARITY
- MIN_LEXICAL_OVERLAP
- MAX_UNSUPPORTED_SENTENCE_RATIO

**Требования реализации**
- Sentence-level verification
- Refusal mode при превышении ratio
- Thresholds configurable
- Логирование результатов проверки

**Acceptance Criteria**
- Hallucinated sentence → refusal
- Threshold validation при старте

**Статус**: Planned  
**Связь**: Anti-hallucination guard

---

## REQ-M6 — Performance Budget Governance

**Параметры**
- SEARCH_P95_BUDGET_MS
- ANSWER_P95_BUDGET_MS
- RERANKER_P95_BUDGET_MS
- EMBEDDINGS_P95_BUDGET_MS

**Требования реализации**
- Сравнение фактического времени с budget
- Event perf_budget_exceeded
- Нет hardcoded budget

**Acceptance Criteria**
- Budget violation логируется
- Конфиг полностью через env

**Статус**: Planned  
**Связь**: Observability

---

## REQ-M7 — Config Validation Layer

**Описание**  
Система должна валидировать критические параметры при старте.

**Проверки**
- alpha ∈ [0,1]
- similarity thresholds ∈ [0,1]
- top_k корректны
- budgets > 0
- reranker_top_k ≤ lex_top_k + vec_top_k

**Acceptance Criteria**
- Некорректный конфиг → fail fast
- Лог critical + exit

**Статус**: Planned

---

## Трассируемость

| Requirement | Affects |
|------------|---------|
| REQ-M1 | embeddings-service |
| REQ-M2 | corporate-rag-service |
| REQ-M3 | retrieval engine |
| REQ-M4 | LLM runner |
| REQ-M5 | anti_hallucination module |
| REQ-M6 | observability |
| REQ-M7 | startup config |


---

## Stage 2/6 (`requirements`) — актуализация реестра

### Каталог текущих требований (baseline)
- `CUR-REQ-01`: memory/lifecycle диалога по tenant/session.
- `CUR-REQ-02`: embedding + indexing + vector retrieval.
- `CUR-REQ-03`: query rewrite/clarification без искажения интента.
- `CUR-REQ-04`: explainable hybrid normalization + memory boosting.
- `CUR-REQ-05`: contextual expansion + token budget assembly.
- `CUR-REQ-06`: grounded generation + conversation summarization.
- `CUR-REQ-07`: ingestion markdown-only + chunking alignment.

Источник детализации: `docs/contracts/requirements_traceability_stage2.md`.

### Кандидаты на расширение (совместимые)
- `EXT-REQ-A`: machine-readable contract -> tests mapping.
- `EXT-REQ-B`: SLO полноты retrieval trace.
- `EXT-REQ-C`: stage-gated quality checklist c min pass policy.

### Результат этапа
- `requirements_catalog` — готов.
- `traceability_matrix` — готов.
- `extension_candidates` — готов.

### Проверка этапа
- Команда: `pytest -q`
- Статус: `warn` (test collection blocked in environment)
- Причина: отсутствуют зависимости `pydantic`, `sqlalchemy`, `pythonjsonlogger`.
