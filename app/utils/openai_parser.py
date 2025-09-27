"""Utilities for parsing OpenAI structured outputs."""
from __future__ import annotations

from typing import Any, Dict, List

EXPECTED_ASPECTS = [
    "price",
    "battery",
    "camera",
    "performance",
    "design",
    "availability",
    "software",
    "support",
    "other",
]


class OpenAIParseError(RuntimeError):
    """Raised when OpenAI response cannot be parsed."""


def parse_sentiment_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate sentiment payload from OpenAI."""

    try:
        sentiment = payload["sentiment"]
        confidence = float(payload["confidence"])
        aspects = payload.get("aspects", {})
    except (KeyError, TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise OpenAIParseError("Invalid sentiment payload") from exc

    if sentiment not in {"positive", "neutral", "negative"}:
        raise OpenAIParseError(f"Unsupported sentiment: {sentiment}")

    normalized_aspects: Dict[str, str] = {}
    for aspect, label in aspects.items():
        if aspect not in EXPECTED_ASPECTS:
            continue
        normalized_aspects[aspect] = str(label)

    return {"sentiment": sentiment, "confidence": confidence, "aspects": normalized_aspects}


def parse_summary_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate summary payload from OpenAI."""

    try:
        overall = str(payload["overall"])
        delights: List[str] = list(payload.get("delights", []))
        pain_points: List[str] = list(payload.get("pain_points", []))
    except (KeyError, TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise OpenAIParseError("Invalid summary payload") from exc

    return {
        "overall": overall,
        "delights": delights[:5],
        "pain_points": pain_points[:5],
    }
