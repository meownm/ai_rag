# Agent Orchestration Guide for `ai_rag`

## Цель
Этот документ предлагает набор специализированных агентов для эволюции текущей кодовой базы RAG-платформы без потери функциональности, с обязательным тестированием и документированием на каждом этапе.

## Рекомендуемый набор агентов

### 1) `codebase-cartographer`
**Задача:** быстро и системно изучает кодовую базу.

**Вход:** дерево проекта, архитектурные документы, OpenAPI, тесты.

**Выход:**
- карта модулей и зависимостей;
- графы вызовов по сервисам (ingestion, retrieval, generation, frontend);
- список «горячих точек» риска (сложность, связность, дубли).

**Артефакты:**
- `docs/architecture.md` (обновление);
- `docs/pipeline_trace.md` (уточнение фактического потока);
- `docs/implementation/implementation-report.md` (секция baseline).

---

### 2) `requirements-miner`
**Задача:** выделяет текущие и потенциальные требования «в духе» существующего решения.

**Вход:**
- текущие контракты в `docs/contracts/*.md`;
- OpenAPI (`openapi/*.yaml`);
- поведение сервисов и UI.

**Выход:**
- каталог требований (функциональные / нефункциональные);
- трассируемость: requirement -> контракт -> тест -> компонент;
- список кандидатов на расширение (без разрыва обратной совместимости).

**Артефакты:**
- `docs/requirements_registry.md` (расширение);
- новые/обновлённые ADR/контрактные заметки в `docs/contracts/`.

---

### 3) `refactor-architect`
**Задача:** перепроектирование и пошаговый рефакторинг кода, БД и интерфейса.

**Вход:** baseline от первых двух агентов.

**Выход:**
- поэтапный план изменений с миграционной стратегией;
- декомпозиция на PR-пакеты (небольшие и проверяемые);
- сохранение контрактов и SLA.

**Артефакты:**
- `docs/implementation/epic-*.md` (план/статус);
- обновления API/схем и UI-слоя при необходимости.

---

### 4) `duplication-slayer`
**Задача:** находит избыточность, дубли и упрощает без потери функциональности.

**Вход:** исходный код + метрики покрытия + отчёты линтеров.

**Выход:**
- реестр дублей (код, запросы, DTO, UI-компоненты);
- замена на общие абстракции/утилиты;
- доказательство эквивалентности через тесты.

**Артефакты:**
- changelog разделов рефакторинга;
- обновлённые тесты (позитивные/негативные/интеграционные).

---

### 5) `contract-scribe`
**Задача:** документирует требования, алгоритмы, структуры данных, контракты и графы вызовов.

**Вход:** изменения из всех PR-пакетов.

**Выход:**
- актуальные контракты API и внутрисервисных границ;
- описания алгоритмов ранжирования/фильтрации/сборки контекста;
- versioned заметки о совместимости.

**Артефакты:**
- `docs/contracts/*.md`;
- `docs/observability.md`;
- `README.md` (если меняется пользовательский поток).

---

### 6) `quality-gatekeeper`
**Задача:** жёстко валидирует каждый этап.

**Вход:** PR-пакет + обновлённые тесты и документация.

**Выход:**
- результаты проверок;
- блокировка merge при нарушении invariants;
- отчёт по регрессиям/покрытию.

**Минимальные проверки:**
- unit: позитивные + негативные сценарии;
- integration/e2e для критических потоков RAG;
- контрактные тесты API;
- smoke UI после изменений интерфейса.

## Как пользоваться агентами (рекомендуемый workflow)

1. **Discovery-этап**
   - Запустить `codebase-cartographer`.
   - Зафиксировать baseline и карту зависимостей.

2. **Requirements-этап**
   - Запустить `requirements-miner`.
   - Обновить реестр требований и трассируемость.

3. **Design/Refactor-этап**
   - Запустить `refactor-architect`.
   - Разбить дорожную карту на маленькие итерации.

4. **Simplification-этап**
   - Запустить `duplication-slayer`.
   - Упростить код при сохранении поведения.

5. **Documentation-этап**
   - Запустить `contract-scribe`.
   - Синхронизировать документацию, контракты и графы вызовов.

6. **Verification-этап**
   - Запустить `quality-gatekeeper`.
   - Принять/отклонить этап по результатам тестов.

## YAML-шаблон оркестрации (строго по порядку)

```yaml
version: 1
workflow:
  - stage: discovery
    agent: codebase-cartographer
    inputs:
      - docs/architecture.md
      - docs/pipeline_trace.md
      - openapi/rag.yaml
      - openapi/embeddings.yaml
    outputs:
      - module_map
      - call_graph
      - risk_hotspots
    checks:
      - pytest -q

  - stage: requirements
    agent: requirements-miner
    inputs:
      - docs/contracts/
      - docs/requirements_registry.md
      - openapi/
    outputs:
      - requirements_catalog
      - traceability_matrix
      - extension_candidates
    checks:
      - pytest -q

  - stage: redesign_refactor
    agent: refactor-architect
    inputs:
      - module_map
      - traceability_matrix
    outputs:
      - refactor_plan
      - migration_strategy
      - pr_batches
    checks:
      - pytest -q

  - stage: simplify
    agent: duplication-slayer
    inputs:
      - pr_batches
      - coverage_report
    outputs:
      - duplication_registry
      - simplification_patches
    checks:
      - pytest -q

  - stage: document
    agent: contract-scribe
    inputs:
      - simplification_patches
      - requirements_catalog
    outputs:
      - updated_contracts
      - updated_algorithm_docs
      - updated_data_structures_docs
    checks:
      - pytest -q

  - stage: verify
    agent: quality-gatekeeper
    inputs:
      - updated_contracts
      - test_results
    outputs:
      - gate_report
      - release_recommendation
    checks:
      - pytest -q
      - python tools/drift_check.py
```

## Практические правила применения
- Не выходить за scope конкретного этапа: один этап -> один измеримый результат.
- Не вырезать функциональность: только эквивалентные рефакторинги или обратно-совместимые расширения.
- При каждом изменении кода обновлять:
  - автоматические тесты;
  - документацию (контракты/алгоритмы/структуры/потоки).
- Для каждого этапа фиксировать тест-лог и статус (pass/fail/warn).

## Definition of Done для этапа
- Все релевантные тесты зелёные.
- Документация синхронизирована с кодом.
- Контракты не нарушены.
- Изменение воспроизводимо (команды запуска/проверки зафиксированы).

## Что делать дальше (практический запуск с нуля)

1. Подготовить окружение и устранить инфраструктурные блокеры тестов:
   - установить зависимости сервисов (`services/corporate-rag-service`, `services/embeddings-service`);
   - запустить базовый прогон `pytest -q` и зафиксировать baseline-ошибки.
2. Выполнить **только stage `discovery`** из YAML и остановиться.
3. Обновить документацию по итогам `discovery`:
   - `docs/architecture.md`;
   - `docs/pipeline_trace.md`;
   - `docs/implementation/implementation-report.md`.
4. После изменений снова запустить проверки stage и записать статус.
5. Переходить к следующему stage только если артефакты текущего stage готовы и результаты проверок зафиксированы.

### Шаблон журнала этапов

```markdown
| stage | scope | changed files | tests command | result | notes |
|---|---|---|---|---|---|
| discovery | module map + call graph | docs/architecture.md, docs/pipeline_trace.md | pytest -q | pass/warn/fail | причины и ссылки |
```

### Минимальный playbook на первые 2 итерации

#### Итерация 1 — Discovery
- Цель: зафиксировать фактическую архитектуру и call graph.
- Разрешённые изменения: только документация архитектуры и трассировки.
- Проверки:
  - `pytest -q`
- Выходные артефакты:
  - `module_map`, `call_graph`, `risk_hotspots`.

#### Итерация 2 — Requirements
- Цель: синхронизировать текущие и потенциальные требования с контрактами.
- Разрешённые изменения: `docs/requirements_registry.md` и релевантные `docs/contracts/*.md`.
- Проверки:
  - `pytest -q`
- Выходные артефакты:
  - `requirements_catalog`, `traceability_matrix`, `extension_candidates`.

## Набор агентов, которые возьмут текущие артефакты и доведут рефакторинг до кода

Ниже — практический состав под ваш запрос «взять уже сделанное исследование/документацию и перейти к реальному рефакторингу кода», сохранив ваши правила: строгий порядок YAML, работа в scope, без вырезания функциональности, с тестами и документированием после каждого шага.

### A. `implementation-batcher` (старт после stage 6)
**Роль:** превращает stage 3/4/5 артефакты в очередь небольших кодовых PR.

**Берёт вход:**
- `docs/implementation/stage3_refactor_plan.md`;
- `docs/implementation/stage4_simplification_registry.md`;
- `docs/contracts/stage5_contracts_sync.md`.

**Делает:**
- формирует batch-план `B1..Bn` (1 batch = 1 bounded change);
- для каждого batch фиксирует scope, риски, rollback;
- связывает batch с требованиями (`CUR-REQ-*`, `EXT-REQ-*`).

**Выход:**
- последовательный backlog рефакторинга с критериями готовности.

### B. `backend-refactor-executor`
**Роль:** вносит эквивалентные рефакторинги в backend без изменения внешних контрактов.

**Scope:**
- сервисный слой (`services/*/app/services`),
- репозитории/DAO,
- общие утилиты и маппинги DTO.

**Обязательства этапа:**
- удаляет дубли/разводит ответственность модулей;
- добавляет/обновляет unit-тесты (позитивные и негативные);
- добавляет интеграционные тесты для затронутого потока;
- синхронизирует документацию по алгоритмам и контрактам.

### C. `data-contract-guardian`
**Роль:** проводит безопасные изменения БД и контрактов миграциями.

**Scope:**
- `alembic` миграции,
- SQLAlchemy модели,
- OpenAPI-совместимость.

**Обязательства этапа:**
- backward-compatible миграции и план отката;
- проверка drift до/после (`python tools/drift_check.py` или `python scripts/drift_detector.py`);
- негативные тесты на ошибочные состояния данных + интеграционные тесты миграции.

### D. `frontend-alignment-agent`
**Роль:** выравнивает интерфейс с обновлённой внутренней архитектурой без изменения UX-контрактов.

**Scope:**
- frontend-компоненты/клиенты API,
- схемы ответа и обработка ошибок.

**Обязательства этапа:**
- упрощение UI-кода и переиспользуемые компоненты;
- позитивные/негативные тесты UI;
- интеграционный smoke критического пользовательского сценария;
- обновление пользовательской документации (`README`/UI docs).

### E. `regression-gatekeeper`
**Роль:** финальная валидация каждого batch перед merge.

**Минимальный набор проверок:**
- unit: позитивные + негативные;
- integration: затронутые сценарии end-to-end;
- contracts/drift: без расхождений с зафиксированными требованиями;
- документация: синхронна коду.

## Как запускать этих агентов по вашему строгому порядку

1. **Не перескакивать stage:** discovery -> requirements -> redesign_refactor -> simplify -> document -> verify.
2. **После `verify` запускать кодовые batch-итерации:**
   - `implementation-batcher` -> `backend-refactor-executor`/`data-contract-guardian`/`frontend-alignment-agent` -> `regression-gatekeeper`.
3. **Для каждой итерации обязательно:**
   - не выходить за объявленный scope;
   - не вырезать функциональность;
   - запускать тесты;
   - фиксировать результат в stage log.

### Шаблон команд проверки для каждой кодовой итерации

```bash
pytest -q
python scripts/drift_detector.py
```

Если проверка не проходит из-за окружения, этап помечается `warn`, причина фиксируется явно, а merge блокируется до снятия блокера.
