from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.analysis import AuditEvent


def log_event(
    db: Session,
    *,
    tender_id: str,
    event_type: str,
    description: str,
    analysis_id: str | None = None,
    actor: str = "system",
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        tender_id=tender_id,
        analysis_id=analysis_id,
        timestamp=datetime.utcnow(),
        event_type=event_type,
        description=description,
        actor=actor,
        event_metadata=metadata,
    )
    db.add(event)
    db.flush()
    return event
