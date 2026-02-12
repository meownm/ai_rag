from __future__ import annotations

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

_METRICS: dict[str, list[int]] = defaultdict(list)


def emit_metric(name: str, value: int) -> None:
    _METRICS[name].append(int(value))


def metric_samples(name: str) -> list[int]:
    return list(_METRICS.get(name, []))


def reset_metrics() -> None:
    _METRICS.clear()


def log_stage_latency(*, stage: str, latency_ms: int, model_id: str, request_id: str) -> None:
    logger.info(
        "rag_stage_latency",
        extra={
            "stage": stage,
            "latency_ms": int(latency_ms),
            "model_id": model_id,
            "request_id": request_id,
        },
    )
