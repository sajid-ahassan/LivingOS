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

    return result
