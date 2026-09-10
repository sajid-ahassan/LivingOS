from langchain_openai import OpenAIEmbeddings

from app.config import get_settings


def get_embedding_model() -> OpenAIEmbeddings:
    settings = get_settings()

    return OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
    )