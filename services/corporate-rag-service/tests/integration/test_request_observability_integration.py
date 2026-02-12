import json

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from app.main import app


def _events(stderr: str) -> list[dict]:
    out = []
    for line in stderr.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def test_every_request_returns_x_request_id_and_access_log(capsys):
    client = TestClient(app)
    response = client.get("/health", headers={"X-Tenant-ID": "tenant-a"})

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")

    events = _events(capsys.readouterr().err)
    access = [e for e in events if e.get("event_type") == "api.request.completed" and e.get("endpoint") == "/health"]
    assert len(access) == 1
    assert access[0]["request_id"] == response.headers["X-Request-ID"]
    assert access[0]["status_code"] == 200
    assert "duration_ms" in access[0]


def test_error_request_logs_error_code(capsys):
    client = TestClient(app)
    response = client.get("/v1/jobs/not-a-uuid")

    assert response.status_code == 422
    events = _events(capsys.readouterr().err)
    access = [e for e in events if e.get("event_type") == "api.request.completed" and e.get("endpoint") == "/v1/jobs/not-a-uuid"]
    assert len(access) == 1
    assert access[0]["error_code"] == "422"


def test_explicit_request_id_header_is_preserved(capsys):
    client = TestClient(app)
    response = client.get("/metrics", headers={"X-Request-ID": "req-fixed-id", "X-Tenant-ID": "tenant-z"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-fixed-id"

    events = _events(capsys.readouterr().err)
    metrics_event = [e for e in events if e.get("event_type") == "metrics_snapshot"]
    access_event = [e for e in events if e.get("event_type") == "api.request.completed" and e.get("endpoint") == "/metrics"]

    assert len(metrics_event) == 1
    assert len(access_event) == 1
    assert metrics_event[0]["request_id"] == "req-fixed-id"
    assert access_event[0]["request_id"] == "req-fixed-id"
