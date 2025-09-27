"""Embedding generation via OpenAI."""
from __future__ import annotations

from typing import List

from app.config import get_settings
from app.utils import backoff
from app.utils.openai_sdk import AsyncOpenAI

settings = get_settings()


class EmbeddingService:
    """Generate embeddings for text payloads."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def embed(self, texts: List[str]) -> List[List[float]]:
        response = await self._client.embeddings.create(
            model=settings.openai_embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]
