import pytest

pytest.importorskip("pydantic")

from app.core.config import Settings


def test_llm_aliases_are_backward_compatible():
    cfg = Settings(OLLAMA_MODEL="legacy-model", OLLAMA_BASE_URL="http://ollama:11434")
    assert cfg.LLM_MODEL == "legacy-model"
    assert cfg.LLM_ENDPOINT == "http://ollama:11434/api/generate"


def test_service_port_aliases_are_backward_compatible():
    cfg = Settings(RAG_SERVICE_PORT=9100)
    assert cfg.SERVICE_PORT == 9100


def test_conflicting_port_aliases_are_rejected(monkeypatch):
    monkeypatch.setenv("SERVICE_PORT", "8100")
    monkeypatch.setenv("RAG_SERVICE_PORT", "8200")
    with pytest.raises(ValueError, match="SERVICE_PORT and RAG_SERVICE_PORT"):
        Settings()


def test_conflicting_llm_aliases_are_rejected(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "new")
    monkeypatch.setenv("OLLAMA_MODEL", "old")
    with pytest.raises(ValueError, match="LLM_MODEL and OLLAMA_MODEL"):
        Settings()