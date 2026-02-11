# EPIC-08 / SP4 — Retrieval Integration and Memory Boosting Contract

## Scope
SP4 integrates rewrite output into retrieval and introduces bounded memory boosting with retrieval trace persistence.

## Retrieval query selection
- If `USE_LLM_QUERY_REWRITE=true`: embeddings/retrieval/rerank use `resolved_query_text`.
- If flag is off: existing raw query path remains unchanged.

## Memory boosting
When conversation context is available (`USE_CONVERSATION_MEMORY=true` with valid conversation header):
- service loads recent `retrieval_trace_items`
- boosting signal comes from prior items where `used_in_answer=true`
- boost is recency-weighted and bounded by cap
- boosting is applied to `final_score` and represented in `boosts_applied` as `memory_reuse_boost`
- scoring timing trace includes `boosted_chunks_count`

## Retrieval trace persistence
For requests with active conversation context, service writes `retrieval_trace_items` for ranked candidates:
- raw lexical/vector/rerank scores
- final score
- usage flags `used_in_context`, `used_in_answer`
- `citation_rank` when present

## Safety and compatibility
- No OpenAPI schema changes.
- Feature flags off preserve previous behavior.
- Tenant scope is preserved through `ConversationRepository` methods.
