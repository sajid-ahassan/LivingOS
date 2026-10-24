"""OFFLINE stand-in for the n8n executor.

With no internet there is no n8n and no GitHub, so approved actions are
applied by calling the mock company adapter in-process, exactly as n8n would
over HTTP. Verification still runs against the database afterwards, so the
action flow (dispatch, succeed, verify, audit) is the same as in LIVE mode.
"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.database import SessionLocal
from app.schemas import MockResourceApplyRequest


def dispatch_offline(payload: dict[str, Any]) -> dict[str, Any]:
    from app.mock_company.service import apply_resource_action

    request = MockResourceApplyRequest(
        action_id=payload["action_id"],
        case_id=payload.get("case_id"),
        person_id=payload["person_id"],
        action_type=payload["action_type"],
        resource_type=payload["resource_type"],
        resource_key=payload["resource_key"],
        requested_data=payload.get("requested_data") or {},
        idempotency_key=payload["idempotency_key"],
    )
    # Its own session, like the separate HTTP request n8n would make.
    with SessionLocal() as db:
        resource, replayed = apply_resource_action(db, request)
        return {
            "status": "SUCCEEDED",
            "execution_id": f"offline-{uuid4()}",
            "external_ref": resource.resource_key,
            "details": {"target": "offline-mock", "replayed": replayed},
        }
