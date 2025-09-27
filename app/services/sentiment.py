"""Sentiment and aspect analysis."""
from __future__ import annotations

from typing import Dict, List

try:  # pragma: no cover - prefer real library
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:  # pragma: no cover - fallback heuristic

    class SentimentIntensityAnalyzer:  # type: ignore
        POSITIVE = {"love", "great", "amazing", "good", "awesome"}
        NEGATIVE = {"hate", "bad", "terrible", "awful", "worse"}

        def polarity_scores(self, text: str) -> Dict[str, float]:  # type: ignore[override]
            tokens = text.lower().split()
            score = 0
            for token in tokens:
                if token in self.POSITIVE:
                    score += 1
                if token in self.NEGATIVE:
                    score -= 1
            return {"compound": max(-1.0, min(1.0, score / max(len(tokens), 1)))}

from app.config import get_settings
from app.utils import backoff
from app.utils.openai_parser import parse_sentiment_payload
from app.utils.openai_sdk import AsyncOpenAI

settings = get_settings()


class SentimentService:
    """Perform sentiment classification using OpenAI with VADER fallback."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._analyzer = SentimentIntensityAnalyzer()

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def classify(self, texts: List[str]) -> List[Dict[str, object]]:
        response = await self._client.responses.create(
            model=settings.openai_model_sentiment,
            input=[
                {
                    "role": "system",
                    "content": "Classify sentiment (positive|neutral|negative) and extract aspects",
                },
                {
                    "role": "user",
                    "content": "\n\n".join(texts),
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "sentiments",
                    "schema": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sentiment": {"type": "string"},
                                "confidence": {"type": "number"},
                                "aspects": {"type": "object"},
                            },
                        },
                    },
                },
            },
        )
        payload = response.output[0].content[0].text  # type: ignore[index]
        import json

        data = json.loads(payload)
        return [parse_sentiment_payload(item) for item in data]

    def fallback(self, texts: List[str]) -> List[Dict[str, object]]:
        results: List[Dict[str, object]] = []
        for text in texts:
            scores = self._analyzer.polarity_scores(text)
            compound = scores["compound"]
            if compound >= 0.05:
                sentiment = "positive"
            elif compound <= -0.05:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            results.append(
                {
                    "sentiment": sentiment,
                    "confidence": abs(compound),
                    "aspects": {},
                    "fallback": True,
                }
            )
        return results
