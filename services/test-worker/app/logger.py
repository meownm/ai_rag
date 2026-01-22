from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any

from prometheus_client import Counter

from .log_contract import normalize

unknown_event_total = Counter("unknown_event_total", "Count of logs with unknown event values", ["app", "event_original"])
unknown_plane_total = Counter("unknown_plane_total", "Count of logs with unknown plane values", ["app", "plane_original"])


class JsonLogger:
    def __init__(self, app: str, env: str, level: str = "INFO") -> None:
        self.app = app
        self.env = env
        self.level = level.upper()

    def _emit(self, level: str, message: str, **fields: Any) -> None:
        plane_in = fields.get("plane")
        event_in = fields.get("event")
        plane, event, plane_orig, event_orig = normalize(plane_in, event_in)

        payload: dict[str, Any] = dict(fields)
        payload["timestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        payload["level"] = level
        payload["app"] = self.app
        payload["env"] = self.env
        payload["plane"] = plane
        payload["event"] = event
        payload["message"] = message

        if plane_orig is not None:
            unknown_plane_total.labels(app=self.app, plane_original=str(plane_orig)).inc()
            payload["log_contract_plane_original"] = str(plane_orig)
        if event_orig is not None:
            unknown_event_total.labels(app=self.app, event_original=str(event_orig)).inc()
            payload["log_contract_event_original"] = str(event_orig)

        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    def info(self, message: str, **fields: Any) -> None:
        self._emit("INFO", message, **fields)

    def warning(self, message: str, **fields: Any) -> None:
        self._emit("WARNING", message, **fields)

    def error(self, message: str, **fields: Any) -> None:
        self._emit("ERROR", message, **fields)

    def exception(self, message: str, exc: Exception, **fields: Any) -> None:
        fields = dict(fields)
        fields["error_type"] = type(exc).__name__
        fields["error_message"] = str(exc)
        self._emit("ERROR", message, **fields)
