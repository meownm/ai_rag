# Pipeline Trace

## Ingest
Client -> gateway /ingest/text -> ingest-service -> app.documents

## Search
Client -> gateway /search -> search-api -> PostgreSQL FTS
