from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import AlertState
from app.ml.features import FEATURES
from app.ml.inference import score_feature_vector
from app.models import AccessEvent, Person


REVIEWABLE_DECISIONS = {
    AlertState.CONFIRMED,
    AlertState.FALSE_POSITIVE,
    AlertState.CLOSED,
}


def _event_bucket(event_type: str) -> str:
    value = (event_type or "").strip().lower()

    if "command" in value:
        return "command"
    if "file" in value:
        return "file"
    if "http" in value or "web" in value or "network" in value:
        return "http"
    if "email" in value or "mail" in value:
        return "email"
    if "device" in value or "usb" in value:
        return "device"
    return "session"


def build_recent_features(
    db: Session,
    *,
    person_id: UUID,
    event_time,
    source: str,
    destination: str,
    event_type: str,
    success: bool,
) -> dict[str, float | int]:
    """
    Build a one-hour approximation of the SPEDIA feature schema from
    LivingOps access_events for this person, including the incoming event.
    """
    window_start = event_time - timedelta(hours=1)

    history = db.scalars(
        select(AccessEvent).where(
            AccessEvent.person_id == person_id,
            AccessEvent.event_time >= window_start,
            AccessEvent.event_time <= event_time,
        )
    ).all()

    events = [
        {
            "source": row.source,
            "destination": row.destination,
            "event_type": row.event_type,
            "success": bool(row.success),
            "event_time": row.event_time,
        }
        for row in history
    ]

    events.append(
        {
            "source": source,
            "destination": destination,
            "event_type": event_type,
            "success": success,
            "event_time": event_time,
        }
    )

    event_count = len(events)
    failed_login_count = sum(
        1
        for e in events
        if (not e["success"])
        and (
            "login" in e["event_type"].lower()
            or "auth" in e["event_type"].lower()
            or "session" in e["event_type"].lower()
        )
    )

    buckets = [_event_bucket(e["event_type"]) for e in events]

    high_severity_count = sum(
        1 for e in events
        if (not e["success"])
    )

    off_hours_count = sum(
        1
        for e in events
        if e["event_time"].hour < 6 or e["event_time"].hour >= 22
    )

    features = {
        "event_count": event_count,
        "failed_login_count": failed_login_count,
        "failed_login_ratio": failed_login_count / max(event_count, 1),
        "command_count": buckets.count("command"),
        "file_event_count": buckets.count("file"),
        "http_count": buckets.count("http"),
        "email_count": buckets.count("email"),
        "device_count": buckets.count("device"),
        "session_count": buckets.count("session"),
        "unique_agents": len({e["source"] for e in events}),
        "unique_decoders": len({e["destination"] for e in events}),
        "unique_actions": len({e["event_type"] for e in events}),
        "high_severity_count": high_severity_count,
        "high_severity_ratio": high_severity_count / max(event_count, 1),
        "off_hours_count": off_hours_count,
        "off_hours_ratio": off_hours_count / max(event_count, 1),
    }

    return {name: features[name] for name in FEATURES}


def create_and_score_access_event(
    db: Session,
    payload,
) -> AccessEvent:
    person = db.get(Person, payload.person_id)
    if person is None:
        raise LookupError("Person not found.")

    features = build_recent_features(
        db,
        person_id=payload.person_id,
        event_time=payload.event_time,
        source=payload.source,
        destination=payload.destination,
        event_type=payload.event_type,
        success=payload.success,
    )

    scoring = score_feature_vector(features)

    event = AccessEvent(
        person_id=payload.person_id,
        event_time=payload.event_time,
        source=payload.source,
        destination=payload.destination,
        event_type=payload.event_type,
        success=payload.success,
        features_data={
            **features,
            "_ml": {
                "threshold": scoring["threshold"],
                "raw_score": scoring["raw_score"],
                "dataset_name": scoring["dataset_name"],
                "code_version": scoring["code_version"],
            },
        },
        anomaly_score=scoring["anomaly_score"],
        alert_status=(
            AlertState.OPEN
            if scoring["is_alert"]
            else AlertState.NONE
        ),
    )

    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_open_security_alerts(db: Session) -> list[AccessEvent]:
    return list(
        db.scalars(
            select(AccessEvent)
            .where(AccessEvent.alert_status == AlertState.OPEN)
            .order_by(
                AccessEvent.anomaly_score.desc(),
                AccessEvent.event_time.desc(),
            )
        ).all()
    )


def review_access_event(
    db: Session,
    *,
    event_id: UUID,
    reviewed_by: UUID,
    decision: AlertState,
    comment: str | None,
) -> AccessEvent:
    event = db.get(AccessEvent, event_id)
    if event is None:
        raise LookupError("Access event not found.")

    reviewer = db.get(Person, reviewed_by)
    if reviewer is None:
        raise LookupError("Reviewer not found.")

    if event.alert_status == AlertState.NONE:
        raise ValueError("This access event has no open security alert.")

    if decision not in REVIEWABLE_DECISIONS:
        raise ValueError(
            "Decision must be CONFIRMED, FALSE_POSITIVE, or CLOSED."
        )

    if event.alert_status == AlertState.OPEN:
        if decision not in {
            AlertState.CONFIRMED,
            AlertState.FALSE_POSITIVE,
        }:
            raise ValueError(
                "OPEN alerts must first become CONFIRMED or FALSE_POSITIVE."
            )
    elif event.alert_status in {
        AlertState.CONFIRMED,
        AlertState.FALSE_POSITIVE,
    }:
        if decision != AlertState.CLOSED:
            raise ValueError(
                "Reviewed alerts may only transition to CLOSED."
            )
    else:
        raise ValueError("This security alert is already closed.")

    event.alert_status = decision
    event.reviewed_by = reviewed_by
    event.review_comment = comment

    db.commit()
    db.refresh(event)
    return event
