import pytest

pytest.importorskip("pythonjsonlogger")

import json
import logging

from app.core.logging import configure_logging


def test_configure_logging_includes_request_id_and_stage_defaults(capsys):
    configure_logging()
    logger = logging.getLogger("test.logging")
    logger.info("event_without_context")

    payload = json.loads(capsys.readouterr().err.strip())
    assert payload["message"] == "event_without_context"
    assert "request_id" in payload
    assert "stage" in payload


def test_configure_logging_preserves_explicit_request_id_and_stage(capsys):
    configure_logging()
    logger = logging.getLogger("test.logging")
    logger.info("event_with_context", extra={"request_id": "req-42", "stage": "metrics"})

    payload = json.loads(capsys.readouterr().err.strip())
    assert payload["request_id"] == "req-42"
    assert payload["stage"] == "metrics"


def test_structured_context_filter_adds_missing_fields():
    from app.core.logging import _StructuredContextFilter

    record = logging.LogRecord(
        name="test.logging",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="evt",
        args=(),
        exc_info=None,
    )

    filt = _StructuredContextFilter()
    assert filt.filter(record) is True
    assert hasattr(record, "request_id")
    assert hasattr(record, "stage")
    assert record.request_id is None
    assert record.stage is None


def test_structured_context_filter_keeps_existing_fields():
    from app.core.logging import _StructuredContextFilter

    record = logging.LogRecord(
        name="test.logging",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="evt",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-existing"
    record.stage = "analysis"

    filt = _StructuredContextFilter()
    assert filt.filter(record) is True
    assert record.request_id == "req-existing"
    assert record.stage == "analysis"
