from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.scripts.seed_company import main as seed_company
from app.scripts.reset_demo import reset_demo_data


DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def _pretty(data: Any) -> None:
    print(json.dumps(data, indent=2, default=str))


def _request(
    method: str,
    path: str,
    *,
    base_url: str,
    body: dict[str, Any] | None = None,
) -> Any:
    url = f"{base_url.rstrip('/')}{path}"

    payload = None
    headers = {"Accept": "application/json"}

    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        url,
        data=payload,
        headers=headers,
        method=method.upper(),
    )

    try:
        with urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return {
                    "status_code": response.status,
                    "message": "No response body.",
                }

            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {
                    "status_code": response.status,
                    "body": raw,
                }

    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw)
        except json.JSONDecodeError:
            detail = raw

        return {
            "error": True,
            "status_code": exc.code,
            "detail": detail,
        }

    except URLError as exc:
        return {
            "error": True,
            "status_code": None,
            "detail": (
                "Could not reach LivingOps API. "
                f"Is uvicorn running at {base_url}? {exc.reason}"
            ),
        }


def health(base_url: str) -> None:
    print("\n=== LivingOps Health ===")
    _pretty(_request("GET", "/health", base_url=base_url))


def seed() -> None:
    print("\n=== Seed Demo Company ===")
    seed_company()


def reset_demo() -> None:
    print("\n=== Reset Demo Environment ===")
    counts = reset_demo_data()

    for name, count in counts.items():
        label = "restored" if name.startswith("restored_") else "removed"
        print(f"{name:20} {label}: {count}")

    print("Demo company restored.")
    print("PolicyVersion rows preserved.")


def show_endpoints(base_url: str) -> None:
    print("\n=== LivingOps API Catalog ===")
    spec = _request("GET", "/openapi.json", base_url=base_url)

    if not isinstance(spec, dict) or "paths" not in spec:
        _pretty(spec)
        return

    for path, operations in spec["paths"].items():
        for method, meta in operations.items():
            if method.lower() not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
            }:
                continue

            summary = meta.get("summary") or meta.get("operationId") or ""
            print(f"{method.upper():7} {path:55} {summary}")


def case_timeline(base_url: str, case_id: str) -> None:
    print("\n=== Case Audit Timeline ===")
    _pretty(
        _request(
            "GET",
            f"/audit/cases/{case_id}/timeline",
            base_url=base_url,
        )
    )


def case_coverage(base_url: str, case_id: str) -> None:
    print("\n=== Case Audit Coverage ===")
    _pretty(
        _request(
            "GET",
            f"/audit/cases/{case_id}/coverage",
            base_url=base_url,
        )
    )


def offboarding_inventory(base_url: str, case_id: str) -> None:
    print("\n=== Offboarding Resource Inventory ===")
    _pretty(
        _request(
            "GET",
            f"/cases/{case_id}/offboarding/inventory",
            base_url=base_url,
        )
    )


def security_alerts(base_url: str) -> None:
    print("\n=== Security Alerts ===")
    _pretty(
        _request(
            "GET",
            "/security/alerts",
            base_url=base_url,
        )
    )


def policy_change(
    base_url: str,
    change_id: str,
) -> None:
    print("\n=== Policy Guardian Change ===")
    _pretty(
        _request(
            "GET",
            f"/policy-guardian/changes/{change_id}",
            base_url=base_url,
        )
    )


def raw_request(
    base_url: str,
    method: str,
    path: str,
    body_text: str | None,
) -> None:
    body = None

    if body_text:
        try:
            body = json.loads(body_text)
        except json.JSONDecodeError as exc:
            raise SystemExit(
                f"Invalid JSON body: {exc}"
            ) from exc

    print(f"\n=== {method.upper()} {path} ===")
    _pretty(
        _request(
            method,
            path,
            base_url=base_url,
            body=body,
        )
    )


def interactive_menu(base_url: str) -> None:
    while True:
        print(
            """
============================================================
 LivingOps AI - Stage 2 Demo Console
============================================================
 1. Health check
 2. Seed deterministic demo people/resources
 3. Reset demo environment
 4. Show API catalog
 5. Show case audit timeline
 6. Show case audit coverage
 7. Show offboarding inventory
 8. Show security alerts
 9. Show Policy Guardian change
10. Make custom API request
 0. Exit
============================================================
""".strip()
        )

        choice = input("\nChoose: ").strip()

        if choice == "0":
            print("Demo console closed.")
            return

        if choice == "1":
            health(base_url)

        elif choice == "2":
            seed()

        elif choice == "3":
            reset_demo()

        elif choice == "4":
            show_endpoints(base_url)

        elif choice == "5":
            case_id = input("Case ID: ").strip()
            case_timeline(base_url, case_id)

        elif choice == "6":
            case_id = input("Case ID: ").strip()
            case_coverage(base_url, case_id)

        elif choice == "7":
            case_id = input("Offboarding case ID: ").strip()
            offboarding_inventory(base_url, case_id)

        elif choice == "8":
            security_alerts(base_url)

        elif choice == "9":
            change_id = input("Policy change ID: ").strip()
            policy_change(base_url, change_id)

        elif choice == "10":
            method = input("HTTP method: ").strip().upper()
            path = input("Path (example /cases/...): ").strip()
            body_text = input(
                "JSON body (leave empty for none): "
            ).strip()
            raw_request(
                base_url,
                method,
                path,
                body_text or None,
            )

        else:
            print("Unknown option.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="LivingOps AI Stage 2 demo CLI"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"LivingOps API base URL (default: {DEFAULT_BASE_URL})",
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("menu")
    sub.add_parser("health")
    sub.add_parser("seed")
    sub.add_parser("reset")
    sub.add_parser("endpoints")
    sub.add_parser("alerts")

    timeline = sub.add_parser("timeline")
    timeline.add_argument("case_id")

    coverage = sub.add_parser("coverage")
    coverage.add_argument("case_id")

    inventory = sub.add_parser("inventory")
    inventory.add_argument("case_id")

    change = sub.add_parser("policy-change")
    change.add_argument("change_id")

    raw = sub.add_parser("request")
    raw.add_argument("method")
    raw.add_argument("path")
    raw.add_argument(
        "--body",
        default=None,
        help="JSON request body",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    command = args.command or "menu"

    if command == "menu":
        interactive_menu(args.base_url)
    elif command == "health":
        health(args.base_url)
    elif command == "seed":
        seed()
    elif command == "reset":
        reset_demo()
    elif command == "endpoints":
        show_endpoints(args.base_url)
    elif command == "alerts":
        security_alerts(args.base_url)
    elif command == "timeline":
        case_timeline(args.base_url, args.case_id)
    elif command == "coverage":
        case_coverage(args.base_url, args.case_id)
    elif command == "inventory":
        offboarding_inventory(args.base_url, args.case_id)
    elif command == "policy-change":
        policy_change(args.base_url, args.change_id)
    elif command == "request":
        raw_request(
            args.base_url,
            args.method,
            args.path,
            args.body,
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
