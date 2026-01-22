# ai_rag

Локальная платформа базы знаний (закрытый тестовый контур). Текущий фокус: подготовка инфраструктуры и базы данных под FTS-only поиск.

## Что уже сделано (EPIC-01)

- Docker Compose стек: PostgreSQL, MinIO, Redis, Grafana/Prometheus/Loki/Promtail, pgAdmin/Adminer/pgHero
- Миграции БД:
  - `app.documents` с `tsvector` и индексами (FTS + trigram)
  - автосоздание ролей и прав из `.env`
- Скрипты `.bat` с минимальными ручными действиями

## Быстрый старт

1. Скопировать `.env.example` в `.env` и при необходимости поменять пароли и порты.
2. Запустить:

```bat
infra\deploy_docker_desktop.bat
```

3. Проверить:

```bat
infra\status.bat
infra\smoke_test.bat
```

## URL по умолчанию (смотрите `.env`)

- pgAdmin: `http://localhost:5701`
- Adminer: `http://localhost:5702`
- pgHero: `http://localhost:5703`
- Grafana: `http://localhost:5602`
- Prometheus: `http://localhost:5601`
- MinIO Console: `http://localhost:5704`
- MinIO API: `http://localhost:5705`

## Структура репозитория

- `infra/` — локальная инфраструктура
- `docs/` — документация (требования, решения, архитектура, пайплайн)
- `services/`, `tgbot/`, `web/` — заглушки под следующие эпики

## Примечание про FTS-only

EPIC-01 не поднимает прикладные API сервисы. В `.env.example` зарезервированы их порты для следующего эпика, но Swagger эндпоинтов пока нет.
