# Requirements Traceability — Stage 2 (`requirements`)

## Scope
- Stage: `requirements` (YAML stage 2/6).
- Purpose: sync current contracts and identify backward-compatible extension candidates.
- Inputs: `docs/contracts/*.md`, `openapi/rag.yaml`, `openapi/embeddings.yaml`, `docs/requirements_registry.md`.

## Current requirements extracted from existing contracts

| Requirement ID | Type | Source contract(s) | Contract intent |
|---|---|---|---|
| CUR-REQ-01 | Functional | `conversation_memory_sp1.md`, `conversation_lifecycle_sp2.md` | Conversation memory must persist lifecycle-aware context per tenant/session boundaries. |
| CUR-REQ-02 | Functional | `embedding_indexing_sp2.md`, `vector_retrieval_sp3.md` | Embedding/index pipeline must support deterministic vector retrieval over indexed chunks. |
| CUR-REQ-03 | Functional | `query_rewriter_sp3.md`, `clarification_loop_sp5.md` | Query understanding may rewrite/clarify before retrieval while preserving user intent. |
| CUR-REQ-04 | Functional | `hybrid_score_normalization_sp4.md`, `retrieval_memory_boosting_sp4.md` | Hybrid scoring requires explainable normalization and optional memory boosting. |
| CUR-REQ-05 | Functional | `contextual_expansion_sp5.md`, `token_budget_assembly_sp6.md` | Context assembly must expand relevant evidence and remain within token budget. |
| CUR-REQ-06 | Functional | `conversation_summarization_sp6.md`, `llm_generation_sp7.md` | LLM generation must be grounded by assembled context and summarization chain. |
| CUR-REQ-07 | Data/Quality | `chunking_spec_v1.md`, `chunking_alignment_sp8.md`, `ingestion_contract_markdown_only.md` | Chunking + ingestion must preserve stable alignment and markdown-only ingestion contract. |

## Requirement -> component/test traceability (baseline)

| Requirement ID | Main components | Existing test surfaces (high level) |
|---|---|---|
| CUR-REQ-01 | `app/db/repositories.py`, `app/api/routes.py` | `services/corporate-rag-service/tests/unit/*conversation*`, integration query flows |
| CUR-REQ-02 | `app/services/retrieval.py`, `app/cli/fts_rebuild.py`, embeddings service routes | `test_fts_retrieval.py`, embeddings integration tests |
| CUR-REQ-03 | `app/runners/query_rewriter.py`, query orchestration in `app/api/routes.py` | unit tests for rewriter + query integration checks |
| CUR-REQ-04 | `app/services/retrieval.py`, `app/services/scoring_trace.py` | scoring/retrieval unit tests + trace tests |
| CUR-REQ-05 | `app/services/context_expansion.py`, `app/services/query_pipeline.py` | query pipeline and context expansion tests |
| CUR-REQ-06 | `app/clients/ollama_client.py`, `app/services/anti_hallucination.py` | anti-hallucination and generation-path tests |
| CUR-REQ-07 | `app/services/ingestion.py`, connectors, chunking contracts | ingestion unit/integration tests |

## Extension candidates (backward-compatible)

1. **EXT-REQ-A: Contract-to-test explicit mapping**
   - Add machine-readable mapping (YAML/JSON) from contract IDs to test suites.
   - Benefit: automatic drift visibility for missing test coverage on a contract.

2. **EXT-REQ-B: Retrieval explainability SLO**
   - Add explicit NFR around trace completeness (`lex/vec/rerank/final/rank`) in success responses.
   - Benefit: clearer acceptance criteria for refactors of ranking pipeline.

3. **EXT-REQ-C: Stage-gated release checklist**
   - Add required quality gates per stage (unit/negative/integration) with minimum pass policy.
   - Benefit: enforces the same process across iterative refactor batches.

## Stage result
- Requirements catalog produced.
- Traceability baseline produced.
- Extension candidates documented.
