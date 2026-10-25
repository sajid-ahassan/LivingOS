from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.config import Settings
from app.enums import ActionState, ActionType, CaseType, ResourceState, ResourceType
from app.execution import service as execution_service
from app.execution.n8n_client import N8NDispatchError, check_reported_status
from app.github.client import GitHubReadClient, GitHubReadError
from app.github.keys import key_title
from app.github.targets import build_github_parameters, build_grant_github_parameters
from app.github.verifier import GitHubVerification, verify_github_action
from app.models import Case, CaseAction, CompanyResource
from app.notifications import service as notifications


N8N_DIR = Path(__file__).resolve().parents[2] / "n8n"


def _settings(**overrides) -> Settings:
    values = {
        "database_url": "postgresql+psycopg://x",
        "qdrant_url": "http://q",
        "qdrant_api_key": "k",
        "openai_api_key": "k",
        "n8n_provisioning_webhook": "http://n8n/exec",
        "n8n_shared_token": "token",
        "n8n_notifier_webhook": "",
        "github_org": "nexora-labs-demo",
        "github_repo": "aurora",
        "github_read_token": "read-token",
        "github_arif_username": "arif-test",
        "github_api_url": "https://api.github.com",
        "demo_mode": "LIVE",
        "app_base_url": "http://127.0.0.1:5173",
        "request_timeout_seconds": 5,
    }
    values.update(overrides)
    return Settings.model_construct(**values)


def _github_access() -> CompanyResource:
    return CompanyResource(
        id=uuid4(),
        person_id=uuid4(),
        resource_type=ResourceType.GITHUB_ACCESS,
        resource_key="github:aurora:arif",
        status=ResourceState.ACTIVE,
        details_data={"github": {"repo": "aurora", "demo_account": "ARIF"}},
        idempotency_key="seed:github",
    )


def _credential(key_id=42, permission="write") -> CompanyResource:
    return CompanyResource(
        id=uuid4(),
        person_id=uuid4(),
        resource_type=ResourceType.AGENT_CREDENTIAL,
        resource_key="credential:aurora-release-bot",
        status=ResourceState.ACTIVE,
        details_data={"permission": permission, "github": {"repo": "aurora", "key_id": key_id}},
        idempotency_key="seed:credential",
    )


def _params(action_type, resource, settings=None):
    return build_github_parameters(
        action_type,
        resource,
        settings=settings or _settings(),
        idempotency_key="case:1:plan:2:action:3",
        new_public_key=lambda title: f"ssh-ed25519 AAAATEST {title}",
    )


# Which actions run against real GitHub


def test_github_is_skipped_without_configuration():
    assert _params(ActionType.REVOKE, _github_access(), _settings(github_read_token="")) is None


def test_github_is_skipped_in_offline_mode():
    assert _params(ActionType.REVOKE, _github_access(), _settings(demo_mode="OFFLINE")) is None


def test_arif_revoke_targets_the_configured_test_account():
    assert _params(ActionType.REVOKE, _github_access()) == {
        "owner": "nexora-labs-demo",
        "repo": "aurora",
        "kind": "collaborator",
        "username": "arif-test",
    }


def test_collaborator_without_username_stays_mock():
    assert _params(ActionType.REVOKE, _github_access(), _settings(github_arif_username="")) is None


def test_credential_without_deploy_key_stays_mock():
    assert _params(ActionType.DOWNSCOPE, _credential(key_id=None)) is None


def test_downscope_rotates_to_a_read_only_key():
    params = _params(ActionType.DOWNSCOPE, _credential())
    title = key_title("credential:aurora-release-bot", "case:1:plan:2:action:3")
    assert params == {
        "owner": "nexora-labs-demo",
        "repo": "aurora",
        "kind": "deploy_key",
        "key_id": 42,
        "key_title": title,
        "public_key": f"ssh-ed25519 AAAATEST {title}",
        "read_only": True,
    }


def test_reassign_rotates_but_keeps_permission():
    assert _params(ActionType.REASSIGN, _credential(permission="write"))["read_only"] is False
    assert _params(ActionType.REASSIGN, _credential(permission="read"))["read_only"] is True


def test_revoke_deletes_the_key_without_a_new_one():
    params = _params(ActionType.REVOKE, _credential())
    assert params["key_id"] == 42
    assert "public_key" not in params


def test_agent_itself_has_no_github_call():
    agent = _credential()
    agent.resource_type = ResourceType.AI_AGENT
    assert _params(ActionType.REASSIGN, agent) is None


def test_key_title_is_stable_and_short():
    first = key_title("credential:aurora-release-bot", "idem-1")
    assert first == key_title("credential:aurora-release-bot", "idem-1")
    assert first != key_title("credential:aurora-release-bot", "idem-2")
    assert len(first) <= 100


def test_generated_public_key_is_openssh_ed25519():
    pytest.importorskip("cryptography")
    from app.github.keys import generate_public_key

    key = generate_public_key("livingops:test")
    assert key.startswith("ssh-ed25519 ")
    assert key.endswith(" livingops:test")


# Independent verification


class FakeGitHub:
    def __init__(self, *, collaborator=False, permission="none", keys=(), error=None):
        self.collaborator = collaborator
        self.permission = permission
        self.keys = list(keys)
        self.error = error

    def _check(self):
        if self.error:
            raise GitHubReadError(self.error)

    def is_collaborator(self, owner, repo, username):
        self._check()
        return self.collaborator

    def collaborator_permission(self, owner, repo, username):
        self._check()
        return self.permission

    def list_deploy_keys(self, owner, repo):
        self._check()
        return self.keys


COLLABORATOR = {"owner": "o", "repo": "aurora", "kind": "collaborator", "username": "arif-test"}
DOWNSCOPE_KEY = {
    "owner": "o", "repo": "aurora", "kind": "deploy_key", "key_id": 42,
    "key_title": "livingops:credential:aurora-release-bot:abc", "read_only": True,
}


def test_revoke_verified_when_collaborator_is_gone():
    result = verify_github_action(ActionType.REVOKE, COLLABORATOR, FakeGitHub(collaborator=False))
    assert result.ok and result.observed == {"collaborator": False}


def test_revoke_fails_when_collaborator_remains():
    result = verify_github_action(ActionType.REVOKE, COLLABORATOR, FakeGitHub(collaborator=True))
    assert not result.ok
    assert "still a collaborator" in result.problems[0]


def test_collaborator_downscope_needs_read_permission():
    assert verify_github_action(ActionType.DOWNSCOPE, COLLABORATOR, FakeGitHub(permission="read")).ok
    assert not verify_github_action(ActionType.DOWNSCOPE, COLLABORATOR, FakeGitHub(permission="write")).ok


def test_key_downscope_verified_and_returns_new_key_id():
    github = FakeGitHub(keys=[{"id": 77, "title": DOWNSCOPE_KEY["key_title"], "read_only": True}])
    result = verify_github_action(ActionType.DOWNSCOPE, DOWNSCOPE_KEY, github)
    assert result.ok
    assert result.new_key_id == 77


def test_key_downscope_fails_if_old_write_key_survives():
    github = FakeGitHub(keys=[
        {"id": 42, "title": "old", "read_only": False},
        {"id": 77, "title": DOWNSCOPE_KEY["key_title"], "read_only": True},
    ])
    result = verify_github_action(ActionType.DOWNSCOPE, DOWNSCOPE_KEY, github)
    assert not result.ok
    assert "old deploy key 42 still exists" in result.problems


def test_key_downscope_fails_if_new_key_can_write():
    github = FakeGitHub(keys=[{"id": 77, "title": DOWNSCOPE_KEY["key_title"], "read_only": False}])
    result = verify_github_action(ActionType.DOWNSCOPE, DOWNSCOPE_KEY, github)
    assert not result.ok
    assert "not read-only" in result.problems[0]


def test_key_downscope_fails_without_the_new_key():
    result = verify_github_action(ActionType.DOWNSCOPE, DOWNSCOPE_KEY, FakeGitHub(keys=[]))
    assert not result.ok


def test_key_revoke_verified_when_key_is_gone():
    params = {k: v for k, v in DOWNSCOPE_KEY.items() if k in {"owner", "repo", "kind", "key_id"}}
    assert verify_github_action(ActionType.REVOKE, params, FakeGitHub(keys=[{"id": 9}])).ok
    assert not verify_github_action(ActionType.REVOKE, params, FakeGitHub(keys=[{"id": 42}])).ok


def test_unreachable_github_is_a_failed_verification_not_a_crash():
    result = verify_github_action(ActionType.REVOKE, COLLABORATOR, FakeGitHub(error="timeout"))
    assert not result.ok
    assert "GitHub check failed" in result.problems[0]


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.requests = []

    def get(self, url, headers, timeout):
        self.requests.append((url, headers))
        return self.responses[url]


def test_read_client_uses_only_get_with_bearer_token():
    base = "https://api.github.com/repos/o/aurora"
    session = FakeSession({
        f"{base}/collaborators/arif": FakeResponse(404),
        f"{base}/collaborators/nabil": FakeResponse(204),
        f"{base}/keys?per_page=100": FakeResponse(200, [{"id": 1}]),
        f"{base}/collaborators/x/permission": FakeResponse(500),
    })
    client = GitHubReadClient(token="read-token", session=session)
    assert client.is_collaborator("o", "aurora", "arif") is False
    assert client.is_collaborator("o", "aurora", "nabil") is True
    assert client.list_deploy_keys("o", "aurora") == [{"id": 1}]
    with pytest.raises(GitHubReadError):
        client.collaborator_permission("o", "aurora", "x")
    assert all(h["Authorization"] == "Bearer read-token" for _, h in session.requests)


# Backend applies only what GitHub confirmed


def _action(action_type, resource, successor=None, github=None) -> CaseAction:
    parameters = {"successor_person_id": str(successor)} if successor else {}
    data = {"sequence": 1, "resource_key": resource.resource_key, "parameters": parameters}
    if github:
        data["github"] = github
    return CaseAction(
        id=uuid4(),
        action_type=action_type,
        resource_type=resource.resource_type,
        requested_data=data,
        status=ActionState.SUCCEEDED,
        idempotency_key="case:1:plan:2:action:3",
    )


def test_verified_downscope_records_new_key_and_new_sponsor():
    credential = _credential()
    nabil = uuid4()
    action = _action(ActionType.DOWNSCOPE, credential, successor=nabil, github=DOWNSCOPE_KEY)
    execution_service._apply_verified_github_change(
        credential, action, GitHubVerification(True, new_key_id=77)
    )
    github = credential.details_data["github"]
    assert github["key_id"] == 77 and github["previous_key_id"] == 42
    assert credential.details_data["permission"] == "read"
    assert credential.person_id == nabil
    assert credential.status == ResourceState.ACTIVE
    assert credential.source_action_id == action.id
    assert credential.details_data["applied_keys"] == {action.idempotency_key: "DOWNSCOPE"}


def test_verified_human_revoke_marks_access_revoked():
    access = _github_access()
    owner = access.person_id
    action = _action(ActionType.REVOKE, access, github=COLLABORATOR)
    execution_service._apply_verified_github_change(access, action, GitHubVerification(True))
    assert access.status == ResourceState.REVOKED
    assert access.person_id == owner


def test_payload_names_its_target():
    case = Case(id=uuid4(), case_type=CaseType.OFFBOARDING, subject_person_id=uuid4())
    mock_action = _action(ActionType.REVOKE, _github_access())
    github_action = _action(ActionType.REVOKE, _github_access(), github=COLLABORATOR)

    mock_payload = execution_service.build_n8n_action_payload(mock_action, case)
    github_payload = execution_service.build_n8n_action_payload(github_action, case)

    assert mock_payload["target"] == "mock"
    assert "github" not in mock_payload["requested_data"]
    assert github_payload["target"] == "github"
    assert github_payload["requested_data"]["github"] == COLLABORATOR


# n8n response and notifications


@pytest.mark.parametrize("status", ["FAILED", "error", "Failure"])
def test_explicit_failure_status_fails_the_action(status):
    with pytest.raises(N8NDispatchError):
        check_reported_status({"status": status, "error": "GitHub 403"})


@pytest.mark.parametrize("body", [{"status": "SUCCEEDED"}, {"resource_key": "x"}])
def test_success_or_legacy_body_is_accepted(body):
    check_reported_status(body)


def test_notification_is_skipped_without_webhook(monkeypatch):
    monkeypatch.setattr(notifications, "get_settings", lambda: _settings())
    result = notifications.notify(
        event_type="APPROVAL_REQUESTED", title="t", summary="s", link_path="workspace.html?case=1"
    )
    assert result.sent is False


def test_notification_failure_never_raises(monkeypatch):
    import requests

    monkeypatch.setattr(
        notifications, "get_settings", lambda: _settings(n8n_notifier_webhook="http://n8n/notify")
    )

    def broken_post(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(notifications.requests, "post", broken_post)
    result = notifications.notify(
        event_type="APPROVAL_REQUESTED", title="t", summary="s", link_path="/guardian.html"
    )
    assert result.sent is False and "unreachable" in result.detail


def test_notification_link_points_at_the_frontend(monkeypatch):
    monkeypatch.setattr(notifications, "get_settings", lambda: _settings())
    message = notifications.build_notification(
        event_type="POLICY_IMPACTS_FOUND", title="t", summary="s",
        link_path="guardian.html?change=9",
    )
    assert message["link"] == "http://127.0.0.1:5173/guardian.html?change=9"


# n8n workflow files


@pytest.mark.parametrize(
    "name", ["livingops-executor", "livingops-notifier", "livingops-expiry-sweeper"]
)
def test_n8n_workflow_files_hold_no_secrets(name):
    workflow = json.loads((N8N_DIR / f"{name}.json").read_text(encoding="utf-8"))
    text = json.dumps(workflow)
    assert workflow["name"] == name
    assert "ghp_" not in text and "github_pat_" not in text
    for node in workflow["nodes"]:
        for credential in (node.get("credentials") or {}).values():
            assert set(credential) == {"name"}


def test_executor_answers_with_status_and_webhooks_need_the_token():
    executor = json.loads((N8N_DIR / "livingops-executor.json").read_text(encoding="utf-8"))
    nodes = {node["name"]: node for node in executor["nodes"]}
    assert nodes["Webhook"]["parameters"]["authentication"] == "headerAuth"
    assert "SUCCEEDED" in nodes["Respond success"]["parameters"]["responseBody"]


# Temporary grants on the demo repository get their own deploy key


def _grant_params(parameters, settings=None):
    return build_grant_github_parameters(
        parameters,
        "credential:aurora-release-bot:grant:abcd1234",
        settings=settings or _settings(),
        idempotency_key="case:1:plan:2:action:3",
        new_public_key=lambda title: f"ssh-ed25519 AAAATEST {title}",
    )


GRANT = {"kind": "temporary_grant", "system": "github", "repository": "aurora",
         "permission": "write", "duration_minutes": 120}


def test_write_grant_on_demo_repo_adds_a_write_key():
    params = _grant_params(GRANT)
    assert params["kind"] == "deploy_key" and params["read_only"] is False
    assert "key_id" not in params
    assert params["key_title"].startswith("livingops:credential:aurora-release-bot:grant:")


def test_read_grant_adds_a_read_only_key():
    assert _grant_params({**GRANT, "permission": "read"})["read_only"] is True


def test_grant_outside_the_demo_repo_or_offline_stays_mock():
    assert _grant_params({**GRANT, "repository": "helios"}) is None
    assert _grant_params(GRANT, _settings(demo_mode="OFFLINE")) is None


def test_verified_grant_creates_the_resource_with_its_key(monkeypatch):
    added = []

    class FakeDb:
        def add(self, row):
            added.append(row)

        def flush(self):
            pass

    monkeypatch.setattr(execution_service, "record_audit_event", lambda db, **kw: None)
    case = Case(id=uuid4(), case_type=CaseType.ACCESS_REQUEST, subject_person_id=uuid4())
    action = CaseAction(
        id=uuid4(),
        action_type=ActionType.GRANT_TEMPORARY,
        resource_type=ResourceType.AGENT_CREDENTIAL,
        requested_data={"resource_key": "credential:aurora-release-bot:grant:abcd1234",
                        "parameters": dict(GRANT)},
        status=ActionState.SUCCEEDED,
        idempotency_key="case:1:plan:2:action:3",
    )
    grant = execution_service._new_github_grant(FakeDb(), action, case, {"repo": "aurora"})
    execution_service._apply_verified_github_change(grant, action, GitHubVerification(True, new_key_id=88))
    assert added == [grant]
    assert grant.person_id == case.subject_person_id
    assert grant.status == ResourceState.ACTIVE
    assert grant.details_data["github"]["key_id"] == 88
    assert grant.details_data["kind"] == "temporary_grant"
    assert grant.source_action_id == action.id


def test_expiry_of_a_github_grant_deletes_its_key():
    grant = _credential(key_id=88)
    grant.resource_key = "credential:aurora-release-bot:grant:abcd1234"
    params = _params(ActionType.REVOKE, grant)
    assert params["kind"] == "deploy_key" and params["key_id"] == 88
