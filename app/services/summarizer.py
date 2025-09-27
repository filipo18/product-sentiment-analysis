"""Generate product summaries."""
from __future__ import annotations

import json
from typing import Dict, List

from app.config import get_settings
from app.utils import backoff
from app.utils.openai_parser import parse_summary_payload
from app.utils.openai_sdk import AsyncOpenAI

settings = get_settings()


class SummaryService:
    """Generate summaries per product/platform."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def summarize(self, product: str, comments: List[str]) -> Dict[str, object]:
        response = await self._client.responses.create(
            model=settings.openai_model_summary,
            input=[
                {
                    "role": "system",
                    "content": "Summarize feedback with delights and pain points",
                },
                {
                    "role": "user",
                    "content": f"Product: {product}\n\nComments:\n" + "\n".join(comments[:200]),
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "summary",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "overall": {"type": "string"},
                            "delights": {"type": "array", "items": {"type": "string"}},
                            "pain_points": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
        )
        payload = response.output[0].content[0].text  # type: ignore[index]
        data = json.loads(payload)
        return parse_summary_payload(data)
