import uuid
from sqlalchemy.orm import Session

from app.models.models import EventLogs


def log_event(db: Session, tenant_id: str, correlation_id: str, event_type: str, payload: dict, duration_ms: int | None = None) -> None:
    db.add(
        EventLogs(
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            event_type=event_type,
            payload_json=payload,
            duration_ms=duration_ms,
        )
    )
    db.commit()
