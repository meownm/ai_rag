# EPIC-02 Merge Snippets (manual)

Этот архив содержит новые файлы и фрагменты для ручного слияния с существующей инфрой.
Файлы в папке `infra_patches/` не заменяют твои текущие, а дают точные вставки.

## 1) docker-compose.infra.yml

### RabbitMQ
Использовать образ `rabbitmq:3-management` и опубликовать порт 15672:

```yaml
image: rabbitmq:3-management
ports:
  - "${INFRA_MQ_PORT:-54040}:5672"
  - "${INFRA_MQ_MGMT_PORT:-54041}:15672"
```

### RabbitMQ exporter
Добавить сервис:

```yaml
rabbitmq-exporter:
  image: prometheuscommunity/rabbitmq-exporter:v0.42.0
  container_name: rag-rabbitmq-exporter
  environment:
    RABBIT_URL: "http://rabbitmq:15672"
    RABBIT_USER: "${INFRA_MQ_USER:-rag_mq}"
    RABBIT_PASSWORD: "${INFRA_MQ_PASSWORD:-rag_mq_pass}"
    PUBLISH_PORT: "9419"
  ports:
    - "${INFRA_MQ_EXPORTER_PORT:-54042}:9419"
  depends_on:
    - rabbitmq
  networks: [rag-net]
```

## 2) infra/.env.infra.example

Добавить:

```env
INFRA_MQ_MGMT_PORT=54041
INFRA_MQ_EXPORTER_PORT=54042
```

## 3) Prometheus prometheus.yml

Добавить job:

```yaml
- job_name: "rabbitmq-exporter"
  static_configs:
    - targets:
        - "rabbitmq-exporter:9419"
```

## 4) Alerts alerts.yml

Добавить:

```yaml
- name: rag-queues
  rules:
    - alert: RabbitMQDLQNotEmpty
      expr: sum by (queue) (rabbitmq_queue_messages{queue=~".*\.dlq"}) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "DLQ not empty"
        description: "Queue {{ $labels.queue }} has messages > 0 for 5m"
```

## 5) docs/ports_registry.md

В секцию Workers (54200–54299):

```md
| test-worker | 54210 | APP_PORT |
```

## 6) Prometheus targets для test-worker

Добавить target `test-worker` на 54210 в твой job workers или static targets.

## 7) verify_infra_consistency.bat

Добавить после текущих проверок:

```bat
python tools\service_generator\verify_queues.py
if errorlevel 1 goto :err
```

## 8) smoke_test_all.bat

Добавить этапы:

```bat
call smoke_cleanup_queues.bat / kb.worker.test-worker
if errorlevel 1 goto :err

call smoke_batch_jobs.bat 50 kb.worker.test-worker
if errorlevel 1 goto :err
```

И DLQ empty gate (если уже есть Prometheus) — оставить/добавить отдельно.
