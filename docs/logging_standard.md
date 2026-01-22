# Logging Standard

## Формат
Все логи — JSON.

## Обязательные поля
- `timestamp` — ISO8601 (добавляет backend логгера)
- `level` — INFO/WARNING/ERROR
- `app` — имя приложения/сервиса
- `env` — окружение
- `request_id` — для HTTP (если применимо)
- `plane` — `control` или `data`
- `event` — enum (см. ниже)
- `message` — человеко-читаемое описание события

## Plane
- `control`: жизненный цикл, инфраструктура, ошибки, probes, старт/остановка, конфигурация.
- `data`: обработка задач и полезные результаты.

## Event enum (минимальный набор)
### Lifecycle
- `startup`
- `shutdown`
- `config_loaded`

### HTTP
- `http_request`
- `http_response`
- `http_error`

### Health / Probes
- `health_check`
- `ready_check`
- `dependency_check`
- `probe_result`
- `probes_started`
- `probes_stopped`

### Worker / Queue
- `worker_started`
- `worker_stopped`
- `job_received`
- `job_ok`
- `job_fail`
- `job_invalid`

### Infra / External
- `db_connected`
- `db_error`
- `redis_connected`
- `redis_error`
- `mq_connected`
- `mq_error`
- `s3_connected`
- `s3_error`

## Поведение при неизвестном event/plane
- лог не блокируется;
- `event` заменяется на `unknown_event`;
- `plane` заменяется на `control`;
- инкрементируются метрики `unknown_event_total`, `unknown_plane_total`.

## LOG_DATA_MODE
- `plain`: ничего не маскировать (тестовый контур).
- `masked`: контент маскируется централизованно.
