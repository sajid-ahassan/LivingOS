import requests


BASE_URL = "http://127.0.0.1:8000"

PAYLOAD = {
    "action_id": "99999999-9999-4999-8999-999999999999",
    "case_id": None,
    "person_id": "44444444-4444-4444-8444-444444444444",
    "action_type": "CREATE",
    "resource_type": "EMAIL_ACCOUNT",
    "resource_key": "email:amina.rahman",
    "requested_data": {
        "address": "amina.rahman@nexora.demo"
    },
    "idempotency_key": "smoke:amina:email:v1",
    "callback_base_url": None,
}


def apply_resource(attempt: int) -> None:
    response = requests.post(
        f"{BASE_URL}/mock/resources/apply",
        json=PAYLOAD,
        timeout=10,
    )

    print()
    print(f"Attempt {attempt}")
    print("HTTP status:", response.status_code)
    print("Response:", response.json())

    response.raise_for_status()


def verify_resource() -> None:
    resource_key = PAYLOAD["resource_key"]

    response = requests.get(
        f"{BASE_URL}/mock/resources/{resource_key}",
        timeout=10,
    )

    print()
    print("Verification status:", response.status_code)
    print("Verified resource:", response.json())

    response.raise_for_status()


def main() -> None:
    apply_resource(attempt=1)
    apply_resource(attempt=2)
    verify_resource()


if __name__ == "__main__":
    main()