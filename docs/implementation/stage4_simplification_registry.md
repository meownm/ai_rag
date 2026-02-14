# Stage 4/6 — Simplification Registry (`duplication-slayer`)

## Scope
- Stage: `simplify` (YAML stage 4/6).
- Goal: выявить избыточности и подготовить безопасные упрощения без изменения функциональности на этом этапе.
- In-scope artifacts: `duplication_registry`, `simplification_patches` (planned).

## Duplication registry (baseline)

| Duplication ID | Area | Observation | Simplification approach | Safety guard |
|---|---|---|---|---|
| DUP-01 | Corporate API routes | `app/api/routes.py` совмещает validation, orchestration, formatting, logging. | Выделить route helpers + orchestration services, сохранить публичные handlers. | Контрактные response tests + integration query/ingest smoke. |
| DUP-02 | Retrieval scoring flow | Повторяющиеся преобразования score/trace между retrieval и trace building. | Вынести нормализацию/trace mapping в единый utility слой. | Unit tests на equality scoring fields + regression fixtures. |
| DUP-03 | Connector error handling | Похожие шаблоны try/retry/timeout между file/s3/confluence connectors. | Общий error/timeout adapter в базовом connector слое. | Negative tests на timeout/auth/fetch failures для каждого connector. |
| DUP-04 | Frontend API mapping | Повтор schema mapping в hooks/pages (`query`, `ingestion`, `diagnostics`). | Централизованный mapper + shared error normalization. | Frontend integration tests для основных страниц. |
| DUP-05 | Stage logs in docs | Повторяющиеся таблицы логов между stage отчётами. | Единый шаблон + ссылка из stage docs. | Док-проверка наличия mandatory полей stage log. |

## Planned simplification patches

1. **PATCH-S4.1**: Decompose route orchestration internals (no API contract changes).
2. **PATCH-S4.2**: Unify retrieval score-to-trace normalization helpers.
3. **PATCH-S4.3**: Standardize connector failure handling pipeline.
4. **PATCH-S4.4**: Consolidate frontend API response mapping.

## Constraints
- Не удалять функциональность.
- Любая simplification patch должна быть покрыта позитивными, негативными и интеграционными тестами в соответствующем PR.
- Контракты OpenAPI/`docs/contracts` менять только при явной необходимости и с обратной совместимостью.

## Stage outputs
- `duplication_registry`: готов.
- `simplification_patches`: готов (как staged plan).
