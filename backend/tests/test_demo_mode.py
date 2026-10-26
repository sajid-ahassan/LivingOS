from __future__ import annotations

from types import SimpleNamespace

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.demo import ai_cache
from app.demo.ai_cache import (
    DemoCacheMiss,
    DemoEmbeddings,
    DemoLLMCache,
    normalize_prompt,
)
from app.execution import n8n_client


ARIF = "66666666-6666-4666-8666-666666666666"
CASE_A = "0b1f6a2e-1111-4c2d-9e3f-aaaaaaaaaaaa"
CASE_B = "7c9d8e1f-2222-4a3b-8c4d-bbbbbbbbbbbb"


class Mode:
    def __init__(self, value: str) -> None:
        self.value = value

    def __call__(self) -> str:
        return self.value


def _model(cache, replies):
    return GenericFakeChatModel(
        messages=iter([AIMessage(content=text) for text in replies]),
        cache=cache,
    )


def _prompt(case_id: str) -> str:
    return f"Plan offboarding for case {case_id}, subject {ARIF}, created 2026-12-26T10:03:00+06:00."


# Prompt normalization


def test_per_run_ids_and_timestamps_are_normalized():
    text = normalize_prompt(_prompt(CASE_A), stable_ids=[ARIF])
    assert CASE_A not in text and "<id>" in text
    assert ARIF in text
    assert "<ts>" in text


def test_dates_without_time_are_kept():
    assert "2026-12-26" in normalize_prompt("last working day 2026-12-26")


def test_two_rehearsals_produce_the_same_key():
    first = normalize_prompt(_prompt(CASE_A), [ARIF])
    second = normalize_prompt(_prompt(CASE_B), [ARIF])
    assert first == second


# LLM cache through LangChain


def test_cached_ai_answers_from_cache_after_first_call(tmp_path):
    cache = DemoLLMCache(tmp_path, mode=Mode("CACHED_AI"), stable_ids=lambda: [ARIF])
    model = _model(cache, ["first answer", "second answer"])

    assert model.invoke(_prompt(CASE_A)).content == "first answer"
    # New case id after reset_demo, same scene: served from the cache.
    assert model.invoke(_prompt(CASE_B)).content == "first answer"
    assert cache.count() == 1


def test_live_mode_always_calls_and_records(tmp_path):
    cache = DemoLLMCache(tmp_path, mode=Mode("LIVE"), stable_ids=lambda: [ARIF])
    model = _model(cache, ["first answer", "second answer"])

    assert model.invoke(_prompt(CASE_A)).content == "first answer"
    assert model.invoke(_prompt(CASE_A)).content == "second answer"
    assert cache.count() == 1


def test_offline_uses_recorded_answers_only(tmp_path):
    mode = Mode("LIVE")
    cache = DemoLLMCache(tmp_path, mode=mode, stable_ids=lambda: [ARIF])
    _model(cache, ["recorded in rehearsal"]).invoke(_prompt(CASE_A))

    mode.value = "OFFLINE"
    offline_model = _model(cache, ["must never be called"])
    assert offline_model.invoke(_prompt(CASE_B)).content == "recorded in rehearsal"
    with pytest.raises(DemoCacheMiss):
        offline_model.invoke("A scene that was never rehearsed")


def test_structured_tool_call_answers_survive_the_cache(tmp_path):
    cache = DemoLLMCache(tmp_path, mode=Mode("CACHED_AI"), stable_ids=lambda: [])
    reply = AIMessage(
        content="",
        tool_calls=[{"name": "OffboardingPlan", "args": {"summary": "Revoke"}, "id": "call_1"}],
    )
    model = GenericFakeChatModel(messages=iter([reply]), cache=cache)
    model.invoke("plan")
    cached = GenericFakeChatModel(messages=iter([]), cache=cache).invoke("plan")
    assert cached.tool_calls[0]["args"] == {"summary": "Revoke"}


def test_invalid_mode_is_rejected(monkeypatch):
    monkeypatch.setattr(ai_cache, "get_settings", lambda: SimpleNamespace(demo_mode="TURBO"))
    with pytest.raises(ValueError):
        ai_cache.current_mode()


# Embeddings cache


class CountingEmbeddings:
    def __init__(self) -> None:
        self.calls = 0

    def embed_documents(self, texts):
        self.calls += 1
        return [[float(len(text)), 1.0] for text in texts]


def test_cached_embeddings_call_openai_once(tmp_path):
    live = CountingEmbeddings()
    embeddings = DemoEmbeddings(live, "text-embedding-3-small", tmp_path, mode=Mode("CACHED_AI"))
    first = embeddings.embed_query("offboarding policy")
    second = embeddings.embed_query("offboarding policy")
    assert first == second
    assert live.calls == 1


def test_only_missing_embeddings_are_fetched(tmp_path):
    live = CountingEmbeddings()
    embeddings = DemoEmbeddings(live, "m", tmp_path, mode=Mode("CACHED_AI"))
    embeddings.embed_documents(["a"])
    embeddings.embed_documents(["a", "bb"])
    assert live.calls == 2
    assert embeddings.count() == 2


def test_offline_embedding_miss_is_an_error(tmp_path):
    embeddings = DemoEmbeddings(CountingEmbeddings(), "m", tmp_path, mode=Mode("OFFLINE"))
    with pytest.raises(DemoCacheMiss):
        embeddings.embed_query("never rehearsed")


# OFFLINE executor


def test_offline_mode_never_calls_n8n(monkeypatch):
    from app.demo import offline_executor

    monkeypatch.setattr(
        n8n_client, "get_settings", lambda: SimpleNamespace(demo_mode="OFFLINE")
    )
    monkeypatch.setattr(
        offline_executor, "dispatch_offline", lambda payload: {"status": "SUCCEEDED", "via": "offline"}
    )

    def no_network(*args, **kwargs):
        raise AssertionError("n8n must not be called in OFFLINE mode")

    monkeypatch.setattr(n8n_client.requests, "post", no_network)
    assert n8n_client.dispatch_to_n8n({"action_id": "x"})["via"] == "offline"


def test_offline_executor_errors_become_dispatch_errors(monkeypatch):
    from app.demo import offline_executor

    monkeypatch.setattr(
        n8n_client, "get_settings", lambda: SimpleNamespace(demo_mode="OFFLINE")
    )

    def broken(payload):
        raise ValueError("resource does not exist")

    monkeypatch.setattr(offline_executor, "dispatch_offline", broken)
    with pytest.raises(n8n_client.N8NDispatchError, match="Offline executor failed"):
        n8n_client.dispatch_to_n8n({"action_id": "x"})


def test_structured_output_survives_the_cache(tmp_path):
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration
    from pydantic import BaseModel

    from app.demo.ai_cache import DemoLLMCache

    class Summary(BaseModel):
        rationale: str

    generation = ChatGeneration(message=AIMessage(content="{}", additional_kwargs={"parsed": Summary(rationale="ok")}))
    cache = DemoLLMCache(tmp_path, mode=lambda: "CACHED_AI")
    cache.update("prompt", "llm", [generation])
    restored = cache.lookup("prompt", "llm")
    assert restored[0].message.additional_kwargs["parsed"] == {"rationale": "ok"}


def test_settings_strip_pasted_newlines(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test\n")
    assert Settings().openai_api_key == "sk-test"


def test_demo_reset_runs_once_in_background(monkeypatch):
    import threading

    from fastapi.testclient import TestClient

    from app.demo import routes
    from app.main import app

    release = threading.Event()
    calls = []
    monkeypatch.setattr("app.github.restore.restore_github_demo", lambda: calls.append("github") or {"skipped": "test"})
    monkeypatch.setattr("app.scripts.reset_demo.reset_demo_data", lambda: release.wait(5) and {"cases": 0})
    client = TestClient(app)
    assert client.post("/demo/reset").json()["state"] == "running"
    assert client.post("/demo/reset").status_code == 409
    release.set()
    for _ in range(50):
        if client.get("/demo/reset").json()["state"] != "running":
            break
        threading.Event().wait(0.05)
    assert client.get("/demo/reset").json()["state"] == "done"
    assert calls == ["github"]
    assert routes._reset_lock.acquire(blocking=False)
    routes._reset_lock.release()
