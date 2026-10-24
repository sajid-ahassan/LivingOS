"""Demo-mode cache for LLM and embedding calls.

DEMO_MODE decides how AI calls behave, so every demo scene gives the same
result whether the venue WiFi works or not:

- LIVE: call OpenAI and record every answer (rehearsals fill the cache).
- CACHED_AI: answer from the cache; call OpenAI only on a miss and record it.
- OFFLINE: answer only from the cache; a miss is an error, never a call.

Cache keys hash the prompt after replacing per-run identifiers (case, plan
and action UUIDs, full timestamps) with placeholders, so a rehearsal after
`reset_demo` hits the answers recorded in an earlier one. Seeded person IDs
are kept because they are stable and change the meaning of a prompt.
Entries live in data/demo_cache/ as JSON and contain no secrets.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

from langchain_core.caches import RETURN_VAL_TYPE, BaseCache
from langchain_core.load import dumps, loads
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, Generation

from app.config import PROJECT_ROOT, get_settings


DEMO_MODES = ("LIVE", "CACHED_AI", "OFFLINE")
CACHE_DIR = PROJECT_ROOT / "data" / "demo_cache"

UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
TIMESTAMP_PATTERN = re.compile(
    r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?\b"
)


# Only model answers may be revived from cache files, never model or client
# objects (which could carry endpoints or headers).
CACHE_ALLOWED_OBJECTS = [
    Generation,
    ChatGeneration,
    ChatGenerationChunk,
    AIMessage,
    AIMessageChunk,
]


class DemoCacheMiss(RuntimeError):
    pass


def current_mode() -> str:
    mode = (get_settings().demo_mode or "LIVE").strip().upper()
    if mode not in DEMO_MODES:
        raise ValueError(f"DEMO_MODE must be one of {DEMO_MODES}, not {mode!r}.")
    return mode


def normalize_prompt(text: str, stable_ids: Iterable[str] = ()) -> str:
    keep = {value.lower() for value in stable_ids}

    def replace_uuid(match: re.Match) -> str:
        value = match.group(0)
        return value if value.lower() in keep else "<id>"

    return TIMESTAMP_PATTERN.sub("<ts>", UUID_PATTERN.sub(replace_uuid, text))


def cache_key(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()


class _Store:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def path(self, key: str) -> Path:
        return self.directory / key[:2] / f"{key}.json"

    def read(self, key: str) -> Any | None:
        path = self.path(key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write(self, key: str, value: Any) -> None:
        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=1, sort_keys=True), encoding="utf-8")

    def count(self) -> int:
        if not self.directory.exists():
            return 0
        return sum(1 for _ in self.directory.glob("*/*.json"))


class DemoLLMCache(BaseCache):
    """LangChain global LLM cache that follows DEMO_MODE."""

    def __init__(
        self,
        directory: Path = CACHE_DIR / "llm",
        *,
        mode: Callable[[], str] = current_mode,
        stable_ids: Callable[[], Iterable[str]] = lambda: (),
    ) -> None:
        self._store = _Store(directory)
        self._mode = mode
        self._stable_ids = stable_ids

    def _key(self, prompt: str, llm_string: str) -> str:
        return cache_key(normalize_prompt(prompt, self._stable_ids()), llm_string)

    def lookup(self, prompt: str, llm_string: str) -> RETURN_VAL_TYPE | None:
        mode = self._mode()
        if mode == "LIVE":
            return None
        stored = self._store.read(self._key(prompt, llm_string))
        if stored is not None:
            return loads(stored["generations"], allowed_objects=CACHE_ALLOWED_OBJECTS)
        if mode == "OFFLINE":
            raise DemoCacheMiss(
                "OFFLINE demo mode has no recorded AI answer for this step; "
                "rehearse it once in LIVE mode first."
            )
        return None

    def update(self, prompt: str, llm_string: str, return_val: RETURN_VAL_TYPE) -> None:
        if self._mode() == "OFFLINE":
            return
        self._store.write(
            self._key(prompt, llm_string),
            {"generations": dumps(list(return_val))},
        )

    def clear(self, **kwargs: Any) -> None:
        raise NotImplementedError("Delete data/demo_cache/llm by hand to clear it.")

    def count(self) -> int:
        return self._store.count()


class DemoEmbeddings:
    """Embeddings wrapper with the same DEMO_MODE behaviour."""

    def __init__(
        self,
        live: Any,
        model_name: str,
        directory: Path = CACHE_DIR / "embeddings",
        *,
        mode: Callable[[], str] = current_mode,
    ) -> None:
        self._live = live
        self._model_name = model_name
        self._store = _Store(directory)
        self._mode = mode

    def _key(self, text: str) -> str:
        return cache_key(self._model_name, text)

    def _embed(self, texts: Sequence[str]) -> list[list[float]]:
        mode = self._mode()
        vectors: list[list[float] | None] = [None] * len(texts)
        missing: list[int] = []
        for index, text in enumerate(texts):
            stored = None if mode == "LIVE" else self._store.read(self._key(text))
            if stored is not None:
                vectors[index] = stored["vector"]
            else:
                missing.append(index)

        if missing:
            if mode == "OFFLINE":
                raise DemoCacheMiss(
                    f"OFFLINE demo mode has no recorded embedding for {len(missing)} "
                    "text(s); rehearse once in LIVE mode first."
                )
            fresh = self._live.embed_documents([texts[i] for i in missing])
            for index, vector in zip(missing, fresh, strict=True):
                vectors[index] = vector
                self._store.write(self._key(texts[index]), {"vector": vector})
        return vectors  # type: ignore[return-value]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]

    def count(self) -> int:
        return self._store.count()


def _seeded_person_ids() -> list[str]:
    from app.scripts.seed_company import all_person_ids

    return [str(person_id) for person_id in all_person_ids()]


_installed: DemoLLMCache | None = None


def install_demo_llm_cache() -> DemoLLMCache:
    """Install the cache as LangChain's global LLM cache (idempotent)."""
    global _installed
    if _installed is None:
        from langchain_core.globals import set_llm_cache

        ids = _seeded_person_ids()
        _installed = DemoLLMCache(stable_ids=lambda: ids)
        set_llm_cache(_installed)
    return _installed
