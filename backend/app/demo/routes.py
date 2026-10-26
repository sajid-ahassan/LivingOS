import threading
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.demo.ai_cache import CACHE_DIR, current_mode, _Store


router = APIRouter(tags=["demo"])


class DemoModeResponse(BaseModel):
    mode: str
    cached_llm_answers: int
    cached_embeddings: int
    github_enabled: bool
    notifier_configured: bool


@router.get("/demo/mode", response_model=DemoModeResponse)
def read_demo_mode() -> DemoModeResponse:
    """What the Dashboard badge shows: the mode and how full the cache is."""
    settings = get_settings()
    mode = current_mode()
    return DemoModeResponse(
        mode=mode,
        cached_llm_answers=_Store(CACHE_DIR / "llm").count(),
        cached_embeddings=_Store(CACHE_DIR / "embeddings").count(),
        github_enabled=settings.github_enabled and mode != "OFFLINE",
        notifier_configured=bool(settings.n8n_notifier_webhook) and mode != "OFFLINE",
    )


# ---------- Demo reset from the UI ----------
# Same work as `python -m app.scripts.reset_demo --yes`: restore the GitHub
# demo org, then the database and policies. It takes minutes, so it runs in
# one background thread and the UI polls its status.
_reset_lock = threading.Lock()
_reset_status: dict = {"state": "idle"}


def _run_reset() -> None:
    from app.github.restore import restore_github_demo
    from app.scripts.reset_demo import reset_demo_data

    try:
        github = restore_github_demo()
        counts = reset_demo_data()
        _reset_status.update(
            state="done", github=github, counts=counts,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as error:  # reported to the UI, never swallowed silently
        _reset_status.update(
            state="failed", error=str(error)[:300],
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        _reset_lock.release()


@router.post("/demo/reset", status_code=202)
def start_demo_reset() -> dict:
    """Reset the demo company, policies and GitHub demo org (runs in the background)."""
    if not _reset_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A demo reset is already running.")
    _reset_status.clear()
    _reset_status.update(state="running", started_at=datetime.now(timezone.utc).isoformat())
    threading.Thread(target=_run_reset, name="demo-reset", daemon=True).start()
    return dict(_reset_status)


@router.get("/demo/reset")
def read_demo_reset() -> dict:
    return dict(_reset_status)
