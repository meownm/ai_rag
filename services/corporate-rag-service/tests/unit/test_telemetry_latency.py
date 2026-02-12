import logging

from app.services.telemetry import emit_metric, log_stage_latency, metric_samples, reset_metrics


def test_emit_metric_accumulates_samples():
    reset_metrics()
    emit_metric("rag_rewrite_latency", 12)
    emit_metric("rag_rewrite_latency", 15)
    assert metric_samples("rag_rewrite_latency") == [12.0, 15.0]


def test_log_stage_latency_structured_fields(caplog):
    caplog.set_level(logging.INFO)
    log_stage_latency(stage="rewrite_agent", latency_ms=21, model_id="model-x", request_id="req-1")

    record = next(r for r in caplog.records if r.message == "rag_stage_latency")
    assert getattr(record, "stage") == "rewrite_agent"
    assert getattr(record, "latency_ms") == 21
    assert getattr(record, "model_id") == "model-x"
    assert getattr(record, "request_id") == "req-1"
