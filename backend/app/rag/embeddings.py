from langchain_openai import OpenAIEmbeddings

from app.config import get_settings
from app.demo.ai_cache import DemoEmbeddings


def get_embedding_model() -> DemoEmbeddings:
    """OpenAI embeddings behind the DEMO_MODE cache (see app.demo.ai_cache)."""
    settings = get_settings()

    live = OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
    )
    return DemoEmbeddings(live, settings.openai_embedding_model)
