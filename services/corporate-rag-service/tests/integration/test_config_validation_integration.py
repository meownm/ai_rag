import pytest

pytest.importorskip("pydantic")

from app.core.config import Settings


def test_settings_accepts_deprecated_port_alias_integration():
    cfg = Settings(RAG_SERVICE_PORT=8111)
    assert cfg.SERVICE_PORT == 8111


def test_settings_rejects_conflicting_endpoint_aliases_integration(monkeypatch):
    monkeypatch.setenv("LLM_ENDPOINT", "http://localhost:11434/api/generate")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11435")
    with pytest.raises(ValueError, match="LLM_ENDPOINT and OLLAMA_BASE_URL"):
        Settings()
