# Queues Observability

## Основные запросы PromQL

### DLQ depth
```promql
sum by (queue) (rabbitmq_queue_messages{queue=~".*\.dlq"})
```

### Retry queue depth
```promql
sum by (queue) (rabbitmq_queue_messages{queue=~".*\.retry"})
```

### Main queue depth
```promql
sum by (queue) (rabbitmq_queue_messages{queue!~".*\.(dlq|retry)"})
```

## Интерпретация
- DLQ > 0: требует разбор причин (unknown_type, max_attempts exceeded).
- Retry > 0 долгое время: деградация downstream или баг обработчика.
- Main растет: producer быстрее consumer, нужно масштабирование worker.
