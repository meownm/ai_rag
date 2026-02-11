# EPIC-REGRESSION-HARDENING — implementation notes

## Implemented safeguards

1. **Model context window verification (RH-SP1 / RH-SP7)**
   - Startup validation now checks `MODEL_CONTEXT_WINDOW` against model/provider `num_ctx` when `VERIFY_MODEL_NUM_CTX=true`.
   - Explicit startup failure uses error code `RH-MODEL-CONTEXT-MISMATCH`.
   - Unknown provider limits are logged as warnings.

2. **Clarification depth enforcement (RH-SP2)**
   - `MAX_CLARIFICATION_DEPTH` is configurable and enforced in clarification loop logic.
   - On overflow, controlled fallback is returned and logged with `RH-CLARIFICATION-DEPTH-EXCEEDED`.

3. **Per-stage latency telemetry (RH-SP3)**
   - Added stage telemetry helper with structured logging fields:
     `stage`, `latency_ms`, `model_id`, `request_id`.
   - Metrics emitted per stage:
     `rag_rewrite_latency`, `rag_retrieval_latency`, `rag_analysis_latency`, `rag_answer_latency`.

4. **Regression golden suite (RH-SP4)**
   - Added golden dataset with 25 retrieval queries and validation tests.

5. **Chunk offset consistency (RH-SP5)**
   - Added tests asserting `markdown[char_start:char_end] == chunk_text` for normalized markdown samples.

6. **Controlled fallback UX (RH-SP6)**
   - Added `CONFIDENCE_FALLBACK_THRESHOLD` and fallback response:
     `Похоже, недостаточно информации для ответа...`.

7. **FSM transition safety tests (RH-SP8)**
   - Added transition coverage tests including error paths and invalid transition rejection.
