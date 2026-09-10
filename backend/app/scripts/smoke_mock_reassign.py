import requests


BASE_URL = "http://127.0.0.1:8000"

ARIF_ID = "66666666-6666-4666-8666-666666666666"
NABIL_ID = "22222222-2222-4222-8222-222222222222"

REASSIGN_PAYLOAD = {
    "action_id": "77777777-7777-4777-8777-777777777777",
    "case_id": None,
    "person_id": ARIF_ID,
    "action_type": "REASSIGN",
    "resource_type": "WORK_ITEM",
    "resource_key": "WORK-AURORA-API",
    "requested_data": {
        "successor_person_id": NABIL_ID,
        "reason": "Employee offboarding",
    },
    "idempotency_key": (
        "smoke:arif:work-aurora-api:reassign:nabil"
    ),
    "callback_base_url": None,
}


def reassign_resource(attempt: int) -> None:
    response = requests.post(
        f"{BASE_URL}/mock/resources/apply",
        json=REASSIGN_PAYLOAD,
        timeout=10,
    )

    print()
    print(f"Reassignment attempt {attempt}")
    print("HTTP status:", response.status_code)
    print("Response:", response.json())

    response.raise_for_status()


def show_inventory(
    person_name: str,
    person_id: str,
) -> None:
    response = requests.get(
        f"{BASE_URL}/mock/people/{person_id}/resources",
        timeout=10,
    )

    response.raise_for_status()
    resources = response.json()

    print()
    print(f"{person_name}'s resources:")

    for resource in resources:
        print(
            "-",
            resource["resource_key"],
            "|",
            resource["status"],
        )


def verify_reassignment() -> None:
    resource_key = REASSIGN_PAYLOAD["resource_key"]

    response = requests.get(
        f"{BASE_URL}/mock/resources/{resource_key}",
        timeout=10,
    )

    response.raise_for_status()
    resource = response.json()

    print()
    print("Verified resource:")
    print("Resource key:", resource["resource_key"])
    print("Current owner:", resource["person_id"])
    print("Status:", resource["status"])
    print("Details:", resource["details_data"])


def main() -> None:
    reassign_resource(attempt=1)
    reassign_resource(attempt=2)

    verify_reassignment()

    show_inventory("Arif", ARIF_ID)
    show_inventory("Nabil", NABIL_ID)


if __name__ == "__main__":
    main()