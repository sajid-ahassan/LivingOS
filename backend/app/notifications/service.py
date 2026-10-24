"""Best-effort notifications through the n8n notifier workflow.

The notifier only tells people that something needs them (an approval, a
Guardian impact). It never decides anything, and a failed notification must
never fail or roll back the business action that triggered it, so errors are
returned, not raised.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

from app.config import get_settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotificationResult:
    sent: bool
    detail: str


def build_notification(
    *,
    event_type: str,
    title: str,
    summary: str,
    link_path: str,
    audience: str | None = None,
) -> dict:
    settings = get_settings()
    base = settings.app_base_url.rstrip("/")
    return {
        "event_type": event_type,
        "title": title[:150],
        "summary": summary[:600],
        "audience": audience,
        "link": f"{base}/{link_path.lstrip('/')}",
        "demo_mode": settings.demo_mode,
    }


def send_notification(message: dict) -> NotificationResult:
    settings = get_settings()
    if not settings.n8n_notifier_webhook:
        logger.info("Notifier not configured; skipped %s", message.get("event_type"))
        return NotificationResult(sent=False, detail="notifier not configured")
    if settings.demo_mode.upper() == "OFFLINE":
        return NotificationResult(sent=False, detail="offline demo mode")

    try:
        response = requests.post(
            settings.n8n_notifier_webhook,
            headers={
                "Authorization": settings.n8n_shared_token,
                "Content-Type": "application/json",
            },
            json=message,
            timeout=settings.request_timeout_seconds,
        )
    except requests.RequestException as error:
        logger.warning("Notification failed: %s", error)
        return NotificationResult(sent=False, detail=f"unreachable: {error}"[:300])

    if not response.ok:
        logger.warning("Notifier returned HTTP %s", response.status_code)
        return NotificationResult(sent=False, detail=f"HTTP {response.status_code}")
    return NotificationResult(sent=True, detail="sent")


def notify(
    *,
    event_type: str,
    title: str,
    summary: str,
    link_path: str,
    audience: str | None = None,
) -> NotificationResult:
    return send_notification(
        build_notification(
            event_type=event_type,
            title=title,
            summary=summary,
            link_path=link_path,
            audience=audience,
        )
    )
