# Structured Observability Logging

## Overview

The service now emits one-line JSON logs for every event through `app.core.logging.log_event`.

Base envelope fields:

- `ts`
- `levelname`
- `service`
- `env`
- `event_type`
- `request_id`
- `tenant_id`
- `plane`
- `version`

## Request correlation

- Middleware reads `X-Request-ID` from incoming requests or generates UUID.
- If client sends `X-Request-ID`, the same value is preserved in response and emitted events.
- `request_id` is exposed back in `X-Request-ID` response header.
- Request/tenant context is propagated via contextvars, so nested logging calls keep the same correlation fields.

## Data-plane events

- `api.request.completed`
- `retrieval.completed` (includes separate `fts_candidates` and `vector_candidates` counts)
- `retrieval.expansion`
- `context.assembly`
- `llm.call.completed`
- `llm.call.error`
- `error.occurred`
- `answer.audit`

## Control-plane events

- `startup.context.verification.*`
- `startup.completed`
- `startup.failed`
- readiness and metrics snapshots

## Sensitive data

- Existing `LOG_DATA_MODE=plain|masked` behavior remains in pipeline payload logging.
- Structured observability events avoid raw secrets and avoid direct PII payload dumps.
