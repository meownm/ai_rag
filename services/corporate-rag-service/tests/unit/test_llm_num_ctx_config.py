import pytest

pytest.importorskip("pydantic")

from app.core.config import Settings


def test_llm_num_ctx_allows_supported_values():
    cfg = Settings(LLM_NUM_CTX=65536, MODEL_CONTEXT_WINDOW=65536, MAX_CONTEXT_TOKENS=65536)
    assert cfg.LLM_NUM_CTX == 65536


def test_llm_num_ctx_rejects_unsupported_values():
    with pytest.raises(ValueError):
        Settings(LLM_NUM_CTX=12345, MODEL_CONTEXT_WINDOW=12345)


def test_model_context_window_must_match_llm_num_ctx_negative():
    with pytest.raises(ValueError, match="MODEL_CONTEXT_WINDOW must be equal"):
        Settings(LLM_NUM_CTX=65536, MODEL_CONTEXT_WINDOW=131072)


def test_max_context_tokens_cannot_exceed_llm_num_ctx_negative():
    with pytest.raises(ValueError, match="MAX_CONTEXT_TOKENS"):
        Settings(LLM_NUM_CTX=65536, MODEL_CONTEXT_WINDOW=65536, MAX_CONTEXT_TOKENS=131072)


def test_vector_retrieval_enabled_by_default():
    cfg = Settings()
    assert cfg.USE_VECTOR_RETRIEVAL is True

def test_hybrid_weight_sum_validation_negative():
    with pytest.raises(ValueError, match="must equal 1.0"):
        Settings(HYBRID_WEIGHT_VECTOR=0.8, HYBRID_WEIGHT_FTS=0.5)


def test_hybrid_weight_upper_bound_negative():
    with pytest.raises(ValueError, match="<= 1.0"):
        Settings(HYBRID_WEIGHT_VECTOR=1.2, HYBRID_WEIGHT_FTS=0.0)
