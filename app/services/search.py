"""Semantic search service."""
from __future__ import annotations

from typing import Dict, List

from app.services.embeddings import EmbeddingService
from app.services.weaviate_client import WeaviateService


class SearchService:
    """Perform semantic search using embeddings and Weaviate."""

    def __init__(self) -> None:
        self._embeddings = EmbeddingService()
        self._weaviate = WeaviateService()

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, object]]:
        vector = (await self._embeddings.embed([query]))[0]
        results = self._weaviate.semantic_search(vector, limit=limit)
        return results
