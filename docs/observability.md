# Observability

## Goals
- End-to-end traceability by `request_id`
- Structured JSON logs (control-plane and data-plane separation)
- Centralized masking by `LOG_DATA_MODE=plain|masked`
- DB log tables for API/search/LLM interactions

## Logging requirements
- JSON per line
- Mandatory fields:
  - `timestamp`
  - `level`
  - `service`
  - `event`
  - `request_id`
  - `duration_ms` (where applicable)
  - `is_success`
- Data-plane payloads:
  - `plain`: store full payloads
  - `masked`: store payload length + metrics, content replaced with placeholder

## Storage constraints
- Max logs size: 30 MB (default)
- Retention: 3 months (default)

## Next steps (implementation)
- Introduce middleware to propagate `request_id`
- Add DB tables:
  - `api_requests_log`
  - `search_requests_log`
  - `llm_requests_log`
