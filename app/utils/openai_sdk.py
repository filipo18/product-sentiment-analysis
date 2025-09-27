"""Wrapper to provide AsyncOpenAI even when SDK is absent."""
from __future__ import annotations

from typing import Any

try:  # pragma: no cover - prefer real SDK
    from openai import AsyncOpenAI  # type: ignore
except ImportError:  # pragma: no cover - fallback for local testing

    class _MissingEndpoint:
        async def create(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("OpenAI SDK is required for this operation")

    class AsyncOpenAI:  # type: ignore
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._responses = _MissingEndpoint()
            self._embeddings = _MissingEndpoint()

        @property
        def responses(self) -> _MissingEndpoint:
            return self._responses

        @property
        def embeddings(self) -> _MissingEndpoint:
            return self._embeddings
