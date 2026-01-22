from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}$"
)


@dataclass(frozen=True)
class Job:
    job_id: str
    type: str
    created_at: str
    payload: dict
    correlation: dict
    attempt: int


def _is_iso8601(s: str) -> bool:
    try:
        x = s.replace("Z", "+00:00")
        datetime.fromisoformat(x)
        return True
    except Exception:
        return False


def validate_job(obj: dict) -> Job:
    for k in ("job_id", "type", "created_at", "payload"):
        if k not in obj:
            raise ValueError(f"missing required field: {k}")

    job_id = obj["job_id"]
    if not isinstance(job_id, str) or not UUID_RE.match(job_id):
        raise ValueError("job_id must be UUID string")

    job_type = obj["type"]
    if not isinstance(job_type, str) or not job_type:
        raise ValueError("type must be non-empty string")

    created_at = obj["created_at"]
    if not isinstance(created_at, str) or not _is_iso8601(created_at):
        raise ValueError("created_at must be ISO8601 string")

    payload = obj["payload"]
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")

    correlation = obj.get("correlation", {})
    if correlation is None:
        correlation = {}
    if not isinstance(correlation, dict):
        raise ValueError("correlation must be object")

    attempt = obj.get("attempt", 0)
    if not isinstance(attempt, int) or attempt < 0:
        raise ValueError("attempt must be integer >= 0")

    return Job(
        job_id=job_id,
        type=job_type,
        created_at=created_at,
        payload=payload,
        correlation=correlation,
        attempt=attempt,
    )
