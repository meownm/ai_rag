import pytest

from app.core.config import Settings


def test_llm_num_ctx_allows_supported_values():
    assert Settings(LLM_NUM_CTX=65536).LLM_NUM_CTX == 65536


def test_llm_num_ctx_rejects_unsupported_values():
    with pytest.raises(ValueError):
        Settings(LLM_NUM_CTX=12345)
