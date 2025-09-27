"""Generate alias expansions for products using OpenAI."""
from __future__ import annotations

import json
from typing import Dict, List

from app.config import get_settings
from app.logging import get_logger
from app.utils import backoff
from app.utils.openai_sdk import AsyncOpenAI

logger = get_logger(__name__)
settings = get_settings()


class AliasHelper:
    """Helper to generate product aliases via OpenAI."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def generate_aliases(self, products: List[str]) -> Dict[str, List[str]]:
        """Generate alias list for each product."""

        response = await self._client.responses.create(
            model=settings.openai_model_sentiment,
            input=[
                {
                    "role": "system",
                    "content": "You expand product names into common aliases.",
                },
                {
                    "role": "user",
                    "content": (
                        "Provide common nicknames, abbreviations, chipset names, and competitor keywords "
                        "for each of the following products. Return JSON object mapping product to alias list.\n"
                        f"Products: {', '.join(products)}"
                    ),
                },
            ],
            response_format={"type": "json_schema", "json_schema": {"name": "aliases", "schema": {"type": "object"}}},
        )
        content = response.output[0].content[0].text  # type: ignore[index]
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse alias response; returning defaults")
            return {product: [product] for product in products}

        normalized: Dict[str, List[str]] = {}
        for product in products:
            aliases = data.get(product) if isinstance(data, dict) else None
            normalized[product] = sorted(set([product] + (aliases or [])))
        return normalized
