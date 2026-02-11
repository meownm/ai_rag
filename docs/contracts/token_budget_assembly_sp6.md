# Token-budget context assembly notes (EPIC-07 SP6)

## Feature flag
- `USE_TOKEN_BUDGET_ASSEMBLY=false` (default): preserve current context budget behavior.
- `USE_TOKEN_BUDGET_ASSEMBLY=true`: assemble context using token budget.
- `MAX_CONTEXT_TOKENS=8000` (default): configurable context token budget.

## Token estimation
- Primary estimator: `tiktoken` (`cl100k_base`) when available.
- Fallback estimator: heuristic `words * 1.33`.
- No runtime downloads are required.

## Assembly behavior
When token budget mode is enabled:
- Chunks are accumulated in order until budget is reached.
- If the first/top chunk alone exceeds budget, it is still included and truncated with marker:
  - `[TRUNCATED_BY_TOKEN_BUDGET]`
- Perf/trace log fields include:
  - `total_context_tokens_est`
  - `max_context_tokens`
  - `truncated`
