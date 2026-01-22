from __future__ import annotations

ALLOWED_PLANES = {"control", "data"}
ALLOWED_EVENTS = {
    "startup",
    "shutdown",
    "config_loaded",
    "http_request",
    "http_response",
    "http_error",
    "health_check",
    "ready_check",
    "dependency_check",
    "probe_result",
    "probes_started",
    "probes_stopped",
    "worker_started",
    "worker_stopped",
    "job_received",
    "job_ok",
    "job_fail",
    "job_invalid",
}

UNKNOWN_EVENT = "unknown_event"
DEFAULT_PLANE = "control"


def normalize(plane: str | None, event: str | None) -> tuple[str, str, str | None, str | None]:
    plane_original = plane if (plane is None or plane not in ALLOWED_PLANES) else None
    event_original = event if (event is None or event not in ALLOWED_EVENTS) else None

    plane_final = DEFAULT_PLANE if plane_original is not None else (plane or DEFAULT_PLANE)
    event_final = UNKNOWN_EVENT if event_original is not None else (event or UNKNOWN_EVENT)
    return plane_final, event_final, plane_original, event_original
