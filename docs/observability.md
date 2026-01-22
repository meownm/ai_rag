# Observability

## Что реально есть в EPIC-01

В EPIC-01 наблюдаемость относится к инфраструктуре Docker Compose:

- **Логи контейнеров** собираются Promtail и пишутся в Loki.
- **Метрики Prometheus** доступны, но в EPIC-01 не добавлены скрейп-таргеты для будущих API сервисов.
- **Grafana** поднимается с преднастроенными datasource для Prometheus и Loki.

## LOG_DATA_MODE

Переменная окружения зарезервирована глобальным стандартом:

- `LOG_DATA_MODE=plain` — ничего не маскируется.
- `LOG_DATA_MODE=masked` — маскирование будет применяться централизованным фильтром в сервисах следующих эпиков.

В EPIC-01 эта переменная только фиксируется в `.env.example` и документации, так как прикладных сервисов нет.

## Как проверить

- Grafana: `http://localhost:${GRAFANA_HOST_PORT}`
- Loki: `http://localhost:${LOKI_HOST_PORT}`
- Prometheus: `http://localhost:${PROMETHEUS_HOST_PORT}`

Сырые логи контейнеров можно проверить через Docker Desktop или `docker logs`.
