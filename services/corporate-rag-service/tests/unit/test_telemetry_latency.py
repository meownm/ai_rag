from app.services.telemetry import emit_metric, log_stage_latency, metric_samples, reset_metrics


def test_emit_metric_accumulates_samples():
    reset_metrics()
    emit_metric("rag_rewrite_latency", 12)
    emit_metric("rag_rewrite_latency", 15)
    assert metric_samples("rag_rewrite_latency") == [12, 15]


def test_log_stage_latency_structured_fields(caplog):
    log_stage_latency(stage="rewrite_agent", latency_ms=21, model_id="model-x", request_id="req-1")
    assert "rag_stage_latency" in caplog.text
