import pytest

pytest.importorskip("pydantic")

from app.core.config import Settings


def test_embeddings_service_port_aliases_are_backward_compatible():
    cfg = Settings(EMBEDDINGS_SERVICE_PORT=9200)
    assert cfg.SERVICE_PORT == 9200


def test_llm_model_aliases_are_backward_compatible():
    cfg = Settings(OLLAMA_MODEL="alias-model")
    assert cfg.LLM_MODEL == "alias-model"


def test_ollama_base_url_is_normalized_for_compatibility():
    cfg = Settings(OLLAMA_BASE_URL="http://ollama:11434")
    assert cfg.LLM_ENDPOINT == "http://ollama:11434/api/generate"


def test_conflicting_port_aliases_raise(monkeypatch):
    monkeypatch.setenv("SERVICE_PORT", "8200")
    monkeypatch.setenv("EMBEDDINGS_SERVICE_PORT", "8300")
    with pytest.raises(ValueError, match="SERVICE_PORT and EMBEDDINGS_SERVICE_PORT"):
        Settings()


def test_conflicting_llm_aliases_raise(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "new")
    monkeypatch.setenv("OLLAMA_MODEL", "old")
    with pytest.raises(ValueError, match="LLM_MODEL and OLLAMA_MODEL"):
        Settings()


def test_invalid_provider_rejected():
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        Settings(LLM_PROVIDER="invalid-provider")
