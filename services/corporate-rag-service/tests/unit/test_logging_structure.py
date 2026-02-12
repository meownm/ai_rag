import json
import logging

import pytest

pytest.importorskip("pythonjsonlogger")

from app.core.logging import clear_request_context, configure_logging, get_request_id, log_event, set_request_context


REQUIRED_FIELDS = {"ts", "levelname", "service", "env", "event_type", "request_id", "tenant_id", "plane", "version", "message"}


def _last_json_line(stderr: str) -> dict:
    lines = [line for line in stderr.splitlines() if line.strip()]
    assert lines
    return json.loads(lines[-1])


def test_configure_logging_includes_unified_envelope(capsys):
    configure_logging()
    logger = logging.getLogger("test.logging")
    logger.info("event_without_context")

    payload = _last_json_line(capsys.readouterr().err)
    assert REQUIRED_FIELDS.issubset(payload.keys())
    assert payload["message"] == "event_without_context"


def test_log_event_uses_request_context(capsys):
    configure_logging()
    set_request_context(request_id="req-42", tenant_id="tenant-9")
    log_event("schema.check", payload={"status_code": 200})

    payload = _last_json_line(capsys.readouterr().err)
    assert payload["event_type"] == "schema.check"
    assert payload["request_id"] == "req-42"
    assert payload["tenant_id"] == "tenant-9"
    assert payload["status_code"] == 200
    clear_request_context()


def test_request_context_lifecycle():
    clear_request_context()
    assert get_request_id() is None
    set_request_context(request_id="req-abc", tenant_id="tenant-abc")
    assert get_request_id() == "req-abc"
    clear_request_context()
    assert get_request_id() is None
