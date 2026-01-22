# Job Retry Policy

## Настройки
- `WORKER_MAX_ATTEMPTS` (default 3)
- `WORKER_RETRY_DELAY_MS` (default 2000)
- `WORKER_RETRY_SUFFIX` (default `.retry`)
- `WORKER_DLQ_SUFFIX` (default `.dlq`)

## Правила
1) invalid message -> ack, result=invalid (без retry и без DLQ).
2) unknown type -> DLQ, result=unknown_type.
3) handler fail:
   - attempt < max_attempts -> publish to retry queue (TTL+DLX), result=retry
   - attempt >= max_attempts -> publish to DLQ, result=dlq

## Топология (без плагинов)
- main: `<queue>`
- retry: `<queue>.retry` с TTL и dead-letter обратно в `<queue>`
- dlq: `<queue>.dlq`
