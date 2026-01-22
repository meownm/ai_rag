# Requirements registry

Статусы: Proposed | Planned | Implemented | Verified | Deprecated

Правило: изменение статусов только после реальной интеграции в код/инфру и проверки.

## Таблица требований

| ID | Требование | Статус | Реализация | Решение |
|---|---|---|---|---|
| RQ-INFRA-0001 | One-click запуск инфраструктуры Docker Desktop через .bat | Verified | `infra\deploy_docker_desktop.bat` | DEC-0001 |
| RQ-INFRA-0002 | Минимум ручных действий: автосоздание `.env` из `.env.example` | Verified | `infra\install.bat` | DEC-0001 |
| RQ-INFRA-0003 | reset-no-confirm для локального контура | Verified | `infra\reset_all.bat` | DEC-0002 |
| RQ-PORTS-0001 | Реестр портов с диапазонами по 100 и выдачей по группам | Implemented | `ports_registry.md`, `.env.example` | DEC-0001 |
| RQ-DB-0001 | Автоматическое создание таблиц и индексов для FTS | Verified | миграции `010`, `011` + migrator | DEC-0001 |
| RQ-DB-0002 | Установка `pg_trgm` и `unaccent` | Verified | `001_extensions.sql` | DEC-0001 |
| RQ-DB-0003 | Автоматическое создание DB-ролей и grants из `.env` | Verified | `run_migrations.sh` (roles+grants) | DEC-0003 |
| RQ-OBS-0001 | Поднять стек наблюдаемости (Grafana/Prometheus/Loki/Promtail) | Implemented | `infra/docker/docker-compose.yml` | DEC-0001 |
| RQ-DOCS-0001 | Наличие обязательного набора документации проекта | Implemented | `docs/*.md` | DEC-0001 |

## Примечания

- EPIC-01 — инфраструктура и FTS-ready база. Реализация поискового API и ingestion будет в следующих эпиках.
