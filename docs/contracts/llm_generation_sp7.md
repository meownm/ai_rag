# SP7 — Optional LLM generation mode (flag-gated)

## Feature flag and defaults
- `USE_LLM_GENERATION=false` (default): preserve retrieval-only answer construction.
- `USE_LLM_GENERATION=true`: enable LLM generation path in `/v1/query`.

## Behavior
- Flag OFF:
  - Query response `answer` is assembled from retrieved context (first two selected chunks concatenated).
  - LLM provider is not called.
- Flag ON:
  - Query pipeline builds prompt from selected chunks and calls configured Ollama endpoint.
  - Request uses `keep_alive=0`.
  - Anti-hallucination verification is executed and attached to trace/log payloads.

## Observability and logging
- LLM logs include `model`, `keep_alive=0`, latency (`t_llm_ms`) and token estimates (`llm_prompt_tokens_est`, `llm_completion_tokens_est`).
- Full prompt/response are logged only when `LOG_DATA_MODE=plain`.
- Response schema remains unchanged.
