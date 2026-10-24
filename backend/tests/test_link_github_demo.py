from __future__ import annotations

from app.scripts.link_github_demo import BOT_KEY_TITLE, apply_bot_key, find_bot_key


def test_finds_exactly_one_bot_key_by_title():
    keys = [{"id": 1, "title": "other"}, {"id": 42, "title": BOT_KEY_TITLE, "read_only": False}]
    assert find_bot_key(keys)["id"] == 42
    assert find_bot_key([]) is None
    assert find_bot_key(keys + [{"id": 43, "title": BOT_KEY_TITLE}]) is None


def test_bot_credential_gets_the_key_id_and_write_permission():
    details = {"agent_key": "agent:aurora-release-bot", "github": {"repo": "aurora", "key_id": None}}
    linked = apply_bot_key(details, 42)
    assert linked["github"]["key_id"] == 42
    assert linked["github"]["repo"] == "aurora"
    assert linked["permission"] == "write"
    assert linked["agent_key"] == "agent:aurora-release-bot"
