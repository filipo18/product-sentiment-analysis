"""Utility functions for text processing."""
from __future__ import annotations

import re
from typing import Iterable, List

WHITESPACE_RE = re.compile(r"\s+")
URL_RE = re.compile(r"https?://\S+")


def normalize_text(text: str) -> str:
    """Lowercase text and collapse whitespace."""

    text = text.strip()
    text = URL_RE.sub("", text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.lower()


def chunked(iterable: Iterable, size: int) -> Iterable[List]:
    """Yield successive chunks from iterable."""

    if size <= 0:
        raise ValueError("size must be positive")

    chunk: List = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk
