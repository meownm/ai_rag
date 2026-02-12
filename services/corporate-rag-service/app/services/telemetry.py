from __future__ import annotations

from collections import defaultdict

from app.core.logging import log_event

_METRICS: dict[str, list[float]] = defaultdict(list)


def emit_metric(name: str, value: float) -> None:
    _METRICS[name].append(float(value))


def metric_samples(name: str) -> list[float]:
    return list(_METRICS.get(name, []))


def reset_metrics() -> None:
    _METRICS.clear()


def log_stage_latency(*, stage: str, latency_ms: int, model_id: str, request_id: str) -> None:
    log_event(
        "rag.stage.latency",
        payload={
            "stage": stage,
            "latency_ms": int(latency_ms),
            "model_id": model_id,
            "request_id": request_id,
        },
        plane="data",
    )
