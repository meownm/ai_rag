# Job Message Contract

## Формат
JSON object.

## Обязательные поля
- `job_id`: string (UUID)
- `type`: string (kebab-case)
- `created_at`: string (ISO8601, UTC)
- `payload`: object

## Опциональные поля
- `correlation`: object
  - `request_id`: string
  - `traceparent`: string
  - `user_id`: string|number (если применимо)
- `attempt`: integer (>=0)

## Правила обработки
- Некорректный JSON или отсутствие обязательных полей -> `job_invalid`, ack (без retry).
- Unknown `type` -> DLQ, ack.
- Ошибка обработчика -> retry до max_attempts, затем DLQ.
