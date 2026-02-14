import pytest

pytest.importorskip("pydantic")

from app.core.config import Settings


def test_settings_accepts_legacy_default_model_id_integration():
    cfg = Settings(DEFAULT_MODEL_ID="legacy-id")
    assert cfg.LLM_MODEL == "legacy-id"


def test_settings_rejects_conflicting_port_aliases_integration(monkeypatch):
    monkeypatch.setenv("SERVICE_PORT", "8200")
    monkeypatch.setenv("PORT", "8300")
    with pytest.raises(ValueError, match="SERVICE_PORT and PORT"):
        Settings()
