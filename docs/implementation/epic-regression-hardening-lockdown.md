# EPIC-REGRESSION-HARDENING — implementation notes

## Implemented safeguards

1. **Model context window verification (RH-SP1 / RH-SP7)**
   - Startup validation now checks `MODEL_CONTEXT_WINDOW` against model/provider `num_ctx` when `VERIFY_MODEL_NUM_CTX=true`.
   - Explicit startup failure uses error code `MODEL_CONTEXT_MISMATCH`.
   - Unknown provider limits are logged as warnings.
   - Startup integration tests now assert FastAPI startup fails with explicit `MODEL_CONTEXT_MISMATCH`.
   - Startup tests use conditional skips when local dependency baseline is incomplete (to avoid false-negative collection errors in stripped environments).

2. **Clarification depth enforcement (RH-SP2)**
   - `MAX_CLARIFICATION_DEPTH` is configurable and enforced in clarification loop logic.
   - `clarification_depth` is now tracked per conversation attempt and persisted in turn metadata/query resolution inputs.
   - On overflow, controlled fallback is returned and logged with `RH-CLARIFICATION-DEPTH-EXCEEDED`.

3. **Per-stage latency telemetry (RH-SP3)**
   - Added stage telemetry helper with structured logging fields:
     `stage`, `latency_ms`, `model_id`, `request_id`.
   - Metrics emitted per stage:
     `rag_rewrite_latency`, `rag_retrieval_latency`, `rag_analysis_latency`, `rag_answer_latency`.
   - Unit tests validate structured fields and mocked integration tests assert stage calls/metric emissions.

4. **Regression golden suite (RH-SP4)**
   - Added golden dataset with 30 retrieval queries and validation tests.
   - Regression tests execute real `hybrid_rank` scoring over deterministic corpus/distractor chunks and assert top document + citation stability.

5. **Chunk offset consistency (RH-SP5)**
   - Added tests asserting `markdown[char_start:char_end] == chunk_text` for normalized markdown samples.

6. **Controlled fallback UX (RH-SP6)**
   - Added `CONFIDENCE_FALLBACK_THRESHOLD` and fallback response:
     `Похоже, недостаточно информации для ответа...`.
   - Boundary tests were added: below-threshold triggers fallback, threshold-equality does not.
   - To preserve existing behavior, retrieval-only mode is not forced into low-confidence fallback; threshold is applied to generated-answer flow.

7. **FSM transition safety tests (RH-SP8)**
   - Added transition coverage tests including error paths and invalid transition rejection.


## EPIC-1 QA follow-up ordering

Implemented in strict RH-1..RH-5 order for Backend/QA review:
1. RH-1 model num_ctx guard and mismatch fail-fast coverage.
2. RH-2 clarification depth enforcement and loop-stop tests.
3. RH-3 stage-level latency structured logging/metrics checks.
4. RH-4 golden regression suite expanded to 30 queries with drift assertions.
5. RH-5 chunk offset integrity checks to prevent trim/strip drift.


## EPIC-2 Agent architecture (AG-1..AG-4)

1. **AG-1 Define Agent interface**
   - Added `BaseAgent` abstraction and strict structured output dataclasses with validation guards.
2. **AG-2 Implement agents**
   - Added concrete `RewriteAgent`, `RetrievalAgent`, `AnalysisAgent`, and `AnswerAgent` implementations.
3. **AG-3 AgentPipeline orchestrator**
   - Added sequential orchestration with explicit `AgentExecutionError`, confidence routing, and clarification-triggered fallback branches.
   - Query requests now pass through `get_agent_pipeline().run(...)` in `post_query`, including clarification-only branches that short-circuit retrieval.
4. **AG-4 Agent trace debug**
   - Added per-agent latency collection and stage output traces; trace is emitted as `AGENT_TRACE` log payload in plain/debug mode.
   - Added integration coverage for clarification-depth exceeded path to assert explicit `RH-CLARIFICATION-DEPTH-EXCEEDED` error logging when pipeline routes to controlled fallback.
