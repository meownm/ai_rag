import uuid
from sqlalchemy.orm import Session

from app.db.repositories import TenantRepository


def log_event(db: Session, tenant_id: str, correlation_id: str, event_type: str, payload: dict, duration_ms: int | None = None) -> None:
    TenantRepository(db, tenant_id).log_event(correlation_id, event_type, payload, duration_ms)
