import pytest

from app.services.startup_guards import StartupValidationError, validate_model_context_windows


class DummyClient:
    def __init__(self, values):
        self.values = values

    def fetch_model_num_ctx(self, model_id=None):
        if model_id is None:
            model_id = "main"
        return self.values.get(model_id)


def test_integration_mismatch_context_window(monkeypatch):
    monkeypatch.setattr("app.services.startup_guards.settings.VERIFY_MODEL_NUM_CTX", True)
    monkeypatch.setattr("app.services.startup_guards.settings.MODEL_CONTEXT_WINDOW", 120000)
    monkeypatch.setattr("app.services.startup_guards.settings.LLM_MODEL", "main")
    monkeypatch.setattr("app.services.startup_guards.settings.REWRITE_MODEL_ID", "rewrite")
    monkeypatch.setattr("app.services.startup_guards.OllamaClient", lambda *_args, **_kwargs: DummyClient({"main": 64000, "rewrite": 64000}))

    with pytest.raises(StartupValidationError) as exc:
        validate_model_context_windows()
    assert exc.value.error_code == "RH-MODEL-CONTEXT-MISMATCH"


def test_integration_skip_verification(monkeypatch):
    monkeypatch.setattr("app.services.startup_guards.settings.VERIFY_MODEL_NUM_CTX", False)
    validate_model_context_windows()
