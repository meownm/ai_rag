# Queue Registry

Источник истины по очередям RabbitMQ в локальном тестовом контуре.

## Схема именования
`<domain>.<capability>.<purpose>` + суффиксы `.retry/.dlq`

## Таблица

| Queue | Producer | Consumer | Purpose | Retry | DLQ | Notes |
|---|---|---|---|:---:|:---:|---|
| kb.worker.test-worker | tools/service_generator/publish_*_jobs.py | test-worker | Smoke test jobs | Y | Y | обязательный e2e |
