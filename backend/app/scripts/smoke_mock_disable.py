import requests


BASE_URL = "http://127.0.0.1:8000"

DISABLE_PAYLOAD = {
    "action_id": "88888888-8888-4888-8888-888888888888",
    "case_id": None,
    "person_id": "44444444-4444-4444-8444-444444444444",
    "action_type": "DISABLE",
    "resource_type": "EMAIL_ACCOUNT",
    "resource_key": "email:amina.rahman",
    "requested_data": {},
    "idempotency_key": "smoke:amina:email:disable:v1",
    "callback_base_url": None,
}


def disable_resource(attempt: int) -> None:
    response = requests.post(
        f"{BASE_URL}/mock/resources/apply",
        json=DISABLE_PAYLOAD,
        timeout=10,
    )

    print()
    print(f"Disable attempt {attempt}")
    print("HTTP status:", response.status_code)
    print("Response:", response.json())

    response.raise_for_status()


def verify_resource() -> None:
    resource_key = DISABLE_PAYLOAD["resource_key"]

    response = requests.get(
        f"{BASE_URL}/mock/resources/{resource_key}",
        timeout=10,
    )

    print()
    print("Verification status:", response.status_code)
    print("Verified resource:", response.json())

    response.raise_for_status()


def main() -> None:
    disable_resource(attempt=1)
    disable_resource(attempt=2)
    verify_resource()


if __name__ == "__main__":
    main()