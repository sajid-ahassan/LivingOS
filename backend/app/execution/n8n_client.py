from typing import Any

import requests

from app.config import get_settings


class N8NDispatchError(RuntimeError):
    pass


def dispatch_to_n8n(
    payload: dict[str, Any],
) -> dict[str, Any]:
    settings = get_settings()

    try:
        response = requests.post(
            settings.n8n_provisioning_webhook,
            headers={
                "Authorization": settings.n8n_shared_token,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=settings.request_timeout_seconds,
        )

    except requests.RequestException as error:
        raise N8NDispatchError(
            f"Could not reach n8n: {error}"
        ) from error

    if not response.ok:
        response_body = response.text.strip()[:500]
        detail = f" Response: {response_body}" if response_body else ""
        raise N8NDispatchError(
            f"n8n returned HTTP {response.status_code}.{detail}"
        )

    try:
        result = response.json()
    except ValueError as error:
        raise N8NDispatchError(
            "n8n returned a non-JSON response."
        ) from error

    if not isinstance(result, dict):
        raise N8NDispatchError(
            "n8n response must be a JSON object."
        )

    check_reported_status(result)
    return result


# A 2xx alone is not trusted: an explicit failure status in the body fails
# the action too. Older workflows that send no status are still accepted;
# verification decides the final outcome either way.
FAILURE_STATUSES = {"FAILED", "FAILURE", "ERROR"}


def check_reported_status(result: dict[str, Any]) -> None:
    reported = result.get("status")
    if isinstance(reported, str) and reported.strip().upper() in FAILURE_STATUSES:
        detail = result.get("error") or result.get("details") or ""
        raise N8NDispatchError(
            f"n8n reported {reported.strip().upper()}"
            + (f": {str(detail)[:300]}" if detail else ".")
        )
