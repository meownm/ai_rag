# corporate-rag-service

## EPIC-08 Conversational RAG flags

The following environment variables were added for conversational memory, rewriting, clarification loop, and summarization. Defaults preserve stateless behavior.

- `USE_CONVERSATION_MEMORY=false`
- `USE_LLM_QUERY_REWRITE=false`
- `USE_CLARIFICATION_LOOP=false`
- `CONVERSATION_TURNS_LAST_N=8`
- `CONVERSATION_SUMMARY_THRESHOLD_TURNS=12`
- `CONVERSATION_TTL_MINUTES=30`
- `REWRITE_CONFIDENCE_THRESHOLD=0.55`
- `REWRITE_MODEL_ID=qwen3:14b-instruct`
- `REWRITE_KEEP_ALIVE=0`
- `REWRITE_MAX_CONTEXT_TOKENS=2048`

See also `.env.example` for runnable defaults.

## Ingestion contract (markdown-only)

Ingestion runtime in this service is markdown-only: crawlers provide markdown `SourceItem` payloads, and no PDF/DOCX byte conversion is performed here.

See: `docs/contracts/ingestion_contract_markdown_only.md`.


## Windows smoke test

```powershell
cd services/corporate-rag-service
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8420
curl -H "X-Conversation-Id: 11111111-1111-1111-1111-111111111111" http://localhost:8420/v1/query -d '{"query":"..."}'
```


## Regression hardening flags

- `MODEL_CONTEXT_WINDOW=8000`
- `VERIFY_MODEL_NUM_CTX=true`
- `MAX_CLARIFICATION_DEPTH=2`
- `ENABLE_PER_STAGE_LATENCY_METRICS=true`
- `CONFIDENCE_FALLBACK_THRESHOLD=0.3`

Startup fails fast with `MODEL_CONTEXT_MISMATCH` when context window is incompatible with provider/model limits.


## EPIC-1 regression checkpoints (RH-1..RH-5)

- **RH-1:** Startup validates `MODEL_CONTEXT_WINDOW <= provider limit` and fails fast with `MODEL_CONTEXT_MISMATCH`.
- **RH-2:** Clarification loop tracks `clarification_depth` and returns controlled fallback when `MAX_CLARIFICATION_DEPTH` is exceeded.
- **RH-3:** Structured stage latency telemetry (`rewrite/retrieval/analysis/answer`) is logged and emitted as metrics when enabled.
- **RH-4:** Regression golden suite includes **30** queries in `tests/regression-suite/golden_queries.json`.
- **RH-5:** Chunk offsets are validated by tests asserting `markdown[char_start:char_end] == chunk_text`, including edge cases sensitive to trimming/normalization.


## EPIC-2 Agent pipeline (AG-1..AG-4)

- **AG-1:** Added base agent contract (`BaseAgent.run(input) -> structured_output`) and validated output schemas in `app/services/agent_pipeline.py`.
- **AG-2:** Implemented `RewriteAgent`, `RetrievalAgent`, `AnalysisAgent`, `AnswerAgent`; each returns validated structured results.
- **AG-3:** Added `AgentPipeline` orchestrator with sequential execution, explicit stage error propagation (`AgentExecutionError`), confidence routing, and clarification-depth fallback routing (including clarification-only turns before retrieval).
- **AG-4:** Added stage trace payload (`stage`, `latency_ms`, and optional debug output) and wired query endpoint to emit `AGENT_TRACE` logs in plain/debug mode.; clarification-depth overflow keeps explicit `RH-CLARIFICATION-DEPTH-EXCEEDED` error logging.


## EPIC-5 observability stop points (OBS-1..OBS-3)

- **OBS-1 Health endpoints:** added `/health`, `/ready`, retained `/v1/health`, and provided compatibility aliases `/v1/ready` + `/v1/metrics`; readiness reports DB and model checks.
- **OBS-2 Metrics:** added `/metrics` snapshot for `token_usage`, `coverage_ratio`, `clarification_rate`, `fallback_rate`; rates are emitted from the final `AgentPipeline` verdict path.
- **OBS-3 Structured logs:** JSON logging now standardizes `request_id` and `stage` keys for every log record.
