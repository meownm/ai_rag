# Stage 3/6 — Redesign & Refactor Plan (`refactor-architect`)

## Scope
- Stage: `redesign_refactor` (YAML order preserved).
- Goal: подготовить план перепроектирования и рефакторинга без изменения runtime-поведения на этом этапе.
- In-scope artifacts: `refactor_plan`, `migration_strategy`, `pr_batches`.

## Refactor plan (high-level)

### Stream A — API orchestration decomposition
- Problem: `services/corporate-rag-service/app/api/routes.py` содержит смешанные ответственности.
- Plan:
  1. Выделить сервисные orchestrator-функции для query/ingestion.
  2. Упростить route-level code до I/O + error mapping.
  3. Сохранить контракт ответа и error envelope без изменений.

### Stream B — Retrieval pipeline modularization
- Problem: цепочка lexical/vector/rerank/context-budget/memory boosting связана в одном потоке.
- Plan:
  1. Ввести явные шаги pipeline через небольшие pure функции.
  2. Зафиксировать вход/выход каждого шага в типизированных структурах.
  3. Добавить regression-guards для explainable scoring полей.

### Stream C — Ingestion connectors normalization
- Problem: разнообразие коннекторов повышает риск дрейфа поведения.
- Plan:
  1. Уточнить единый контракт connector fetch result.
  2. Стандартизировать обработку ошибок/таймаутов.
  3. Синхронизировать markdown-only ingestion ограничения с тестами.

### Stream D — Frontend contract alignment
- Problem: риск рассинхронизации UI типов и backend контракта.
- Plan:
  1. Актуализировать typed schemas и mapping слои.
  2. Стабилизировать отображение trace/debug блоков при частичных ответах.
  3. Добавить интеграционные проверки query/ingestion страниц.

## Migration strategy
1. **No-break phase**: только внутренние refactor изменения за feature parity тестами.
2. **Dual-path phase**: при необходимости временно поддерживать старый и новый internal path с флагом.
3. **Cutover phase**: удалить legacy-path после подтверждённого parity по unit + integration.
4. **Stabilization phase**: запустить drift checks и зафиксировать release checklist.

## Proposed PR batches

| Batch | Scope | Planned files | Required tests |
|---|---|---|---|
| PR-3.1 | API route decomposition | `app/api/routes.py`, `app/services/query_pipeline.py` | unit (+negative), integration query path |
| PR-3.2 | Retrieval modularization | `app/services/retrieval.py`, `app/services/scoring_trace.py` | unit retrieval/scoring, integration retrieval |
| PR-3.3 | Ingestion connector normalization | `app/services/connectors/*`, `app/services/ingestion.py` | unit connectors (+negative), integration ingestion |
| PR-3.4 | Frontend alignment | `frontend/src/api/*`, `frontend/src/pages/*`, `frontend/src/test/*` | frontend unit/integration tests |
| PR-3.5 | Cleanup and parity gates | touched by previous PRs | full stage checks + drift |

## Guardrails
- Не удалять функциональность.
- Для каждого PR: позитивные + негативные тесты, где применимо интеграционные.
- Изменения контрактов только через явное обновление OpenAPI и docs/contracts.

## Stage outputs
- `refactor_plan`: готов.
- `migration_strategy`: готов.
- `pr_batches`: готов.
