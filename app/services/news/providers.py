"""News providers stub."""
from __future__ import annotations

from typing import Dict, List


class NewsProvider:
    """Base provider interface."""

    name: str = "base"

    async def fetch(self, query: str) -> List[Dict[str, str]]:  # pragma: no cover - interface
        raise NotImplementedError


class NewsAPIProvider(NewsProvider):
    """NewsAPI provider stub disabled in v1."""

    name = "newsapi"

    async def fetch(self, query: str) -> List[Dict[str, str]]:
        return []
