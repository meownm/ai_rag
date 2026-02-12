import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")
from fastapi.testclient import TestClient

from app.main import app


class DummyClient:
    def __init__(self, values):
        self.values = values

    def fetch_model_num_ctx(self, model_id=None):
        model_key = str(model_id or "main")
        return self.values.get(model_key)


def test_startup_fails_with_mismatch_error_code(monkeypatch):
    from app.services import startup_guards

    monkeypatch.setattr(startup_guards.settings, "VERIFY_MODEL_NUM_CTX", True)
    monkeypatch.setattr(startup_guards.settings, "MODEL_CONTEXT_WINDOW", 120000)
    monkeypatch.setattr(startup_guards.settings, "LLM_MODEL", "main")
    monkeypatch.setattr(startup_guards.settings, "REWRITE_MODEL_ID", "rewrite")
    monkeypatch.setattr(
        startup_guards,
        "OllamaClient",
        lambda *_args, **_kwargs: DummyClient({"main": 64000, "rewrite": 64000}),
    )

    with pytest.raises(RuntimeError) as exc:
        with TestClient(app):
            pass

    assert "MODEL_CONTEXT_MISMATCH" in str(exc.value)


def test_startup_succeeds_when_verification_disabled(monkeypatch):
    from app.services import startup_guards

    monkeypatch.setattr(startup_guards.settings, "VERIFY_MODEL_NUM_CTX", False)
    with TestClient(app):
        assert True
