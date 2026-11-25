"""Append-only audit trail helper."""
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def log_event(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: Any = None,
    actor_type: str = "system",
    actor_id: Any = None,
    request_id: uuid.UUID | None = None,
    meta: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_type=actor_type,
        actor_id=str(actor_id) if actor_id is not None else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        request_id=request_id,
        meta=meta or {},
    )
    db.add(entry)
    return entry
