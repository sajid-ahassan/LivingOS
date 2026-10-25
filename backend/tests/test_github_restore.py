from __future__ import annotations

import pytest

from app.github import restore
from app.scripts.link_github_demo import BOT_KEY_TITLE
from test_github_execution import FakeGitHub, _settings


def _key_fn(title):
    return f"ssh-ed25519 AAAATEST {title}"


def _plan(keys, arif="write"):
    return restore.plan_restore(keys, arif, settings=_settings(), new_public_key=_key_fn)


def test_clean_org_needs_no_calls():
    assert _plan([{"id": 1, "title": BOT_KEY_TITLE, "read_only": False}]) == []


def test_after_a_rehearsal_strays_go_bot_key_and_arif_come_back():
    keys = [
        {"id": 5, "title": "livingops:credential:aurora-release-bot:abc", "read_only": True},
        {"id": 6, "title": "someone-elses-key", "read_only": False},
    ]
    calls = _plan(keys, arif="none")
    assert [c["action_type"] for c in calls] == ["REVOKE", "REASSIGN", "DOWNSCOPE"]
    assert calls[0]["requested_data"]["github"]["key_id"] == 5
    added = calls[1]["requested_data"]["github"]
    assert added["key_title"] == BOT_KEY_TITLE and added["read_only"] is False
    assert "key_id" not in added
    arif = calls[2]["requested_data"]["github"]
    assert arif == {"owner": "nexora-labs-demo", "repo": "aurora", "kind": "collaborator",
                    "username": "arif-test", "permission": "push"}
    assert all(c["target"] == "github" for c in calls)


def test_read_only_bot_key_is_replaced_not_kept():
    calls = _plan([{"id": 1, "title": BOT_KEY_TITLE, "read_only": True}])
    assert [c["action_type"] for c in calls] == ["REVOKE", "REASSIGN"]


def test_restore_is_skipped_offline_or_unconfigured():
    assert "skipped" in restore.restore_github_demo(settings=_settings(demo_mode="OFFLINE"))
    assert "skipped" in restore.restore_github_demo(settings=_settings(github_read_token=""))


class SequenceGitHub(FakeGitHub):
    """Returns the 'before' keys first and the 'after' keys from then on."""

    def __init__(self, before, after, permissions):
        super().__init__()
        self.listings = [before, after]
        self.permissions = list(permissions)

    def list_deploy_keys(self, owner, repo):
        return self.listings.pop(0) if len(self.listings) > 1 else self.listings[0]

    def collaborator_permission(self, owner, repo, username):
        return self.permissions.pop(0) if len(self.permissions) > 1 else self.permissions[0]


def test_restore_dispatches_checks_github_and_saves_the_key(monkeypatch):
    saved = {}
    monkeypatch.setattr(restore, "load_demo_ids", lambda: {"other": 1})
    monkeypatch.setattr(restore, "save_demo_ids", saved.update)
    sent = []
    github = SequenceGitHub(
        before=[{"id": 5, "title": "livingops:x", "read_only": True}],
        after=[{"id": 9, "title": BOT_KEY_TITLE, "read_only": False}],
        permissions=["none", "none"],
    )
    report = restore.restore_github_demo(
        settings=_settings(), client=github, dispatch=sent.append, new_public_key=_key_fn
    )
    assert len(sent) == 3
    assert saved == {"other": 1, "aurora_release_bot_key_id": 9}
    assert report == {"github_calls": 3, "bot_key_id": 9, "arif_access": "invitation pending"}


def test_restore_fails_when_github_did_not_change(monkeypatch):
    monkeypatch.setattr(restore, "save_demo_ids", lambda values: None)
    github = SequenceGitHub(before=[], after=[], permissions=["write"])
    with pytest.raises(RuntimeError, match="No single write deploy key"):
        restore.restore_github_demo(
            settings=_settings(), client=github, dispatch=lambda p: {}, new_public_key=_key_fn
        )
