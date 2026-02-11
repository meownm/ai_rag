import pytest

from app.services.startup_guards import StartupValidationError, validate_model_context_windows


class DummyClient:
    def __init__(self, ctx_by_model):
        self.ctx_by_model = ctx_by_model

    def fetch_model_num_ctx(self, model_id=None):
        if model_id is None:
            model_id = "default"
        return self.ctx_by_model.get(model_id)


def test_startup_fails_when_model_context_window_exceeds_actual(monkeypatch):
    monkeypatch.setattr("app.services.startup_guards.settings.VERIFY_MODEL_NUM_CTX", True)
    monkeypatch.setattr("app.services.startup_guards.settings.MODEL_CONTEXT_WINDOW", 9000)
    monkeypatch.setattr("app.services.startup_guards.settings.LLM_MODEL", "main")
    monkeypatch.setattr("app.services.startup_guards.settings.REWRITE_MODEL_ID", "rewrite")
    monkeypatch.setattr("app.services.startup_guards.OllamaClient", lambda *_args, **_kwargs: DummyClient({"main": 8000, "rewrite": 8000}))

    with pytest.raises(StartupValidationError) as exc:
        validate_model_context_windows()
    assert exc.value.error_code == "RH-MODEL-CONTEXT-MISMATCH"


def test_startup_succeeds_when_verification_disabled(monkeypatch):
    monkeypatch.setattr("app.services.startup_guards.settings.VERIFY_MODEL_NUM_CTX", False)
    validate_model_context_windows()


def test_provider_limit_mismatch_raises(monkeypatch):
    monkeypatch.setattr("app.services.startup_guards.settings.VERIFY_MODEL_NUM_CTX", True)
    monkeypatch.setattr("app.services.startup_guards.settings.MODEL_CONTEXT_WINDOW", 8192)
    monkeypatch.setattr("app.services.startup_guards.settings.LLM_MODEL", "main")
    monkeypatch.setattr("app.services.startup_guards.settings.REWRITE_MODEL_ID", "rewrite")
    monkeypatch.setattr("app.services.startup_guards.OllamaClient", lambda *_args, **_kwargs: DummyClient({"main": 8192, "rewrite": 4096}))

    with pytest.raises(StartupValidationError) as exc:
        validate_model_context_windows()
    assert exc.value.error_code == "RH-MODEL-CONTEXT-MISMATCH"


def test_unknown_provider_limit_logs_warning(monkeypatch, caplog):
    monkeypatch.setattr("app.services.startup_guards.settings.VERIFY_MODEL_NUM_CTX", True)
    monkeypatch.setattr("app.services.startup_guards.settings.MODEL_CONTEXT_WINDOW", 4096)
    monkeypatch.setattr("app.services.startup_guards.settings.LLM_MODEL", "main")
    monkeypatch.setattr("app.services.startup_guards.settings.REWRITE_MODEL_ID", "rewrite")
    monkeypatch.setattr("app.services.startup_guards.OllamaClient", lambda *_args, **_kwargs: DummyClient({"main": 8192, "rewrite": None}))

    validate_model_context_windows()
    assert "provider_context_limit_unknown" in caplog.text
