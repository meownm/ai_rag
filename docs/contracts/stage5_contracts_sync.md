# Stage 5/6 — Contracts & Documentation Sync (`contract-scribe`)

## Scope
- Stage: `document` (YAML stage 5/6).
- Goal: синхронизировать требования, алгоритмы, структуры данных, контракты и call-graph артефакты после stage 1-4.
- In-scope outputs: `updated_contracts`, `updated_algorithm_docs`, `updated_data_structures_docs`.

## Updated contracts baseline

### API contract surfaces (no breaking changes)
- `openapi/rag.yaml` and `openapi/embeddings.yaml` remain authoritative API contracts.
- Stage 5 introduces **documentation synchronization only**; endpoint behavior is unchanged.

### Internal contract synchronization
- Retrieval path contract:
  - input: sanitized query + tenant scope + optional history/trace context;
  - output: ranked grounded contexts + explainable score trace fields.
- Ingestion path contract:
  - input: source descriptors/connectors;
  - output: normalized markdown artifacts + chunk/link persistence.
- Guard contract:
  - anti-hallucination verification may force structured refusal while preserving response envelope shape.

## Algorithms (synced summary)
- Hybrid retrieval: lexical + vector candidate merge with rerank and optional memory/context expansion steps.
- Token budget assembly: deterministic context selection bounded by budget and stage budgets.
- Generation and guard: grounded generation followed by citation validation and refusal fallback.

## Data structures (synced summary)
- Query trace structure: contains per-candidate explainability fields (`lex`, `vec`, `rerank`, `final`, `rank`) in trace payload.
- Ingestion structures: stable chunk IDs + link relations + source version metadata.
- Error envelope: stable machine-readable error object with correlation id and retryability attributes.

## Call graph synchronization
- Frontend -> corporate-rag-service -> embeddings-service / Ollama preserved.
- Stage-level docs now consistently reference this call graph across architecture/pipeline/implementation artifacts.

## Stage outputs
- `updated_contracts`: documented.
- `updated_algorithm_docs`: documented.
- `updated_data_structures_docs`: documented.
