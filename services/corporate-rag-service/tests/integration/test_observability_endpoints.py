import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.services.telemetry import emit_metric, reset_metrics


class HealthyDB:
    def execute(self, *_args, **_kwargs):
        return object()


class FailingDB:
    def execute(self, *_args, **_kwargs):
        raise RuntimeError("db unavailable")


class FakeOllamaClient:
    def fetch_model_num_ctx(self, _model_id):
        return 4096


class FailingOllamaClient:
    def fetch_model_num_ctx(self, _model_id):
        raise RuntimeError("model probe failed")


def _override_db(db):
    def _dep():
        yield db

    return _dep


def test_health_and_ready_and_metrics_success(monkeypatch):
    from app.api import routes

    reset_metrics()
    emit_metric("token_usage", 123)
    emit_metric("coverage_ratio", 0.75)
    emit_metric("clarification_rate", 1)
    emit_metric("fallback_rate", 0)

    monkeypatch.setattr(routes, "get_ollama_client", lambda: FakeOllamaClient())
    app.dependency_overrides[get_db] = _override_db(HealthyDB())

    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    ready = client.get("/ready")
    assert ready.status_code == 200
    ready_body = ready.json()
    assert ready_body["status"] == "ok"
    assert ready_body["checks"]["db"]["ok"] is True
    assert ready_body["checks"]["model"]["ok"] is True

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    metric_body = metrics.json()["metrics"]
    assert metric_body["token_usage"]["latest"] == 123.0
    assert metric_body["coverage_ratio"]["latest"] == 0.75
    assert metric_body["clarification_rate"]["avg"] == 1.0
    assert metric_body["fallback_rate"]["avg"] == 0.0

    ready_v1 = client.get("/v1/ready")
    assert ready_v1.status_code == 200
    assert ready_v1.json()["status"] == "ok"

    metrics_v1 = client.get("/v1/metrics")
    assert metrics_v1.status_code == 200
    assert metrics_v1.json()["status"] == "ok"


@pytest.mark.parametrize(
    ("db", "client_factory", "check_name"),
    [
        (FailingDB(), lambda routes: FakeOllamaClient(), "db"),
        (HealthyDB(), lambda routes: FailingOllamaClient(), "model"),
    ],
)
def test_ready_returns_degraded_on_failed_dependency(monkeypatch, db, client_factory, check_name):
    from app.api import routes

    monkeypatch.setattr(routes, "get_ollama_client", lambda: client_factory(routes))
    app.dependency_overrides[get_db] = _override_db(db)

    client = TestClient(app)
    response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"][check_name]["ok"] is False
    assert body["checks"][check_name]["detail"]


def test_v1_ready_returns_degraded_on_failed_model(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes, "get_ollama_client", lambda: FailingOllamaClient())
    app.dependency_overrides[get_db] = _override_db(HealthyDB())

    client = TestClient(app)
    response = client.get("/v1/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["model"]["ok"] is False
    assert "model probe failed" in body["checks"]["model"]["detail"]
