from typing import Any
from uuid import UUID, uuid4

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.enums import AuditActorType
from app.models import AuditEvent


def record_audit_event(
    db: Session,
    *,
    actor_type: AuditActorType,
    event_type: str,
    entity_type: str,
    entity_id: UUID,
    actor_id: UUID | None = None,
    before_data: dict[str, Any] | None = None,
    after_data: dict[str, Any] | None = None,
    evidence_data: dict[str, Any] | None = None,
    correlation_id: UUID | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_type=actor_type,
        actor_id=actor_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        before_data=jsonable_encoder(before_data) if before_data else None,
        after_data=jsonable_encoder(after_data) if after_data else None,
        evidence_data=jsonable_encoder(evidence_data) if evidence_data else None,
        correlation_id=correlation_id or uuid4(),
    )

    db.add(event)
    db.flush()

    return event