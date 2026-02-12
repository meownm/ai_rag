from __future__ import annotations

import contextvars
import json
import logging
from datetime import datetime, timezone
from typing import Any

from pythonjsonlogger import jsonlogger

from app.core.config import settings

_request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
_tenant_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("tenant_id", default=None)


class JsonLineFormatter(jsonlogger.JsonFormatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = super().format(record)
        return json.dumps(json.loads(payload), separators=(",", ":"), ensure_ascii=False)


class _StructuredContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        request_id = _request_id_ctx.get()
        tenant_id = _tenant_id_ctx.get()
        if not hasattr(record, "request_id") or record.request_id is None:
            record.request_id = request_id
        if not hasattr(record, "tenant_id") or record.tenant_id is None:
            record.tenant_id = tenant_id
        if not hasattr(record, "event_type"):
            record.event_type = None
        if not hasattr(record, "plane"):
            record.plane = None
        if not hasattr(record, "service"):
            record.service = settings.APP_NAME
        if not hasattr(record, "env"):
            record.env = "local"
        if not hasattr(record, "version"):
            record.version = settings.APP_VERSION
        if not hasattr(record, "ts"):
            record.ts = datetime.now(timezone.utc).isoformat()
        return True


def set_request_context(*, request_id: str | None = None, tenant_id: str | None = None) -> None:
    _request_id_ctx.set(request_id)
    _tenant_id_ctx.set(tenant_id)


def clear_request_context() -> None:
    set_request_context(request_id=None, tenant_id=None)


def get_request_id() -> str | None:
    return _request_id_ctx.get()


def get_tenant_id() -> str | None:
    return _tenant_id_ctx.get()


def log_event(
    event_type: str,
    *,
    level: int = logging.INFO,
    payload: dict[str, Any] | None = None,
    tenant_id: str | None = None,
    request_id: str | None = None,
    plane: str = "data",
) -> None:
    logger = logging.getLogger("app.observability")
    extra = {
        "event_type": event_type,
        "plane": plane,
        "request_id": request_id if request_id is not None else get_request_id(),
        "tenant_id": tenant_id if tenant_id is not None else get_tenant_id(),
        "ts": datetime.now(timezone.utc).isoformat(),
        "service": settings.APP_NAME,
        "env": "local",
        "version": settings.APP_VERSION,
    }
    if payload:
        extra.update(payload)
    logger.log(level, event_type, extra=extra)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.addFilter(_StructuredContextFilter())
    formatter = JsonLineFormatter(
        "%(ts)s %(levelname)s %(service)s %(env)s %(event_type)s %(request_id)s %(tenant_id)s %(plane)s %(version)s %(message)s"
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]
