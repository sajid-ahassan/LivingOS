from fastapi import APIRouter
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
