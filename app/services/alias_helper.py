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
        try:
            # Minimal request without response_format for broader SDK compatibility
            response = await self._client.responses.create(
                model=settings.openai_model_sentiment,
                input=[
                    {"role": "system", "content": "You expand product names into common aliases."},
                    {
                        "role": "user",
                        "content": (
                            "Provide common nicknames, abbreviations, chipset names, and competitor keywords "
                            "for each of the following products. Return a JSON object mapping each product to an alias list.\n"
                            f"Products: {', '.join(products)}"
                        ),
                    },
                ],
            )

            # Try to extract text in a version-tolerant way
            content: str | None = getattr(response, "output_text", None)
            if not content:
                # Fallback to older structure
                content = response.output[0].content[0].text  # type: ignore[index]

            data = json.loads(content or "{}")
            normalized: Dict[str, List[str]] = {}
            for product in products:
                aliases = data.get(product) if isinstance(data, dict) else None
                normalized[product] = sorted(set([product] + (aliases or [])))
            return normalized
        except Exception as exc:
            logger.warning(f"Alias generation failed, using defaults: {exc}")
            # Safe, local fallback aliases so the app continues to work
            fallback: Dict[str, List[str]] = {}
            for p in products:
                variants = [p]
                pl = p.lower()
                if pl != p:
                    variants.append(pl)
                nospace = pl.replace(" ", "")
                if nospace not in variants:
                    variants.append(nospace)
                fallback[p] = variants
            return fallback

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def suggest_subreddits(self, products: List[str]) -> List[str]:
        """Suggest relevant subreddit names for the given products using OpenAI.

        Returns a list of subreddit names (without the leading 'r/'). Product-agnostic.
        """
        try:
            prompt = (
                "Given a list of products, suggest the most relevant subreddit names "
                "to monitor current discussions about these products. Return ONLY a JSON array "
                "of subreddit names as strings (no descriptions, no 'r/' prefix), strictly no extra keys or text. "
                "Avoid very generic subs unless they are highly active for the topic. Prefer brand/model or closely adjacent communities.\n"
                f"Products: {', '.join(products)}"
            )
            response = await self._client.responses.create(
                model=settings.openai_model_sentiment,
                input=[
                    {"role": "system", "content": "You return only a JSON array of subreddit names."},
                    {"role": "user", "content": prompt},
                ],
            )
            content: str | None = getattr(response, "output_text", None)
            if not content:
                content = response.output[0].content[0].text  # type: ignore[index]

            data = json.loads(content or "[]")
            candidates: List[str] = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str) and item.strip():
                        name = item.strip()
                        if name.startswith("r/"):
                            name = name[2:]
                        candidates.append(name)

            # Score by overlap with product tokens to stay domain-agnostic
            def to_tokens(items: List[str]) -> set[str]:
                import re
                tokens: set[str] = set()
                for it in items:
                    for tok in re.split(r"[^a-zA-Z0-9]+", it.lower()):
                        if tok and len(tok) > 1:
                            tokens.add(tok)
                return tokens

            product_tokens = to_tokens(products)
            unique_candidates = list({c for c in candidates if c})
            scored = sorted(
                unique_candidates,
                key=lambda s: sum(tok in s.lower() for tok in product_tokens),
                reverse=True,
            )
            return scored[:20]
        except Exception as exc:
            logger.warning(f"Subreddit suggestion failed, returning empty list: {exc}")
            return []

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def suggest_reddit_queries(self, products: List[str]) -> List[str]:
        """Suggest high-signal Reddit search queries for finding up-to-date discussions.

        Returns a JSON array of query strings (Reddit search syntax), product-agnostic.
        """
        try:
            prompt = (
                "Given a list of products, propose Reddit search queries that will surface up-to-date "
                "discussions in relevant subreddits. Use Reddit search syntax, including quoted phrases and OR "
                "where helpful, but keep each query under 128 characters. Return ONLY a JSON array of query strings, "
                "no extra keys or text.\n"
                f"Products: {', '.join(products)}"
            )
            response = await self._client.responses.create(
                model=settings.openai_model_sentiment,
                input=[
                    {"role": "system", "content": "You return only a JSON array of query strings."},
                    {"role": "user", "content": prompt},
                ],
            )
            content: str | None = getattr(response, "output_text", None)
            if not content:
                content = response.output[0].content[0].text  # type: ignore[index]

            data = json.loads(content or "[]")
            queries: List[str] = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        q = item.strip()
                        if q:
                            queries.append(q[:128])
            # Dedupe preserve order, cap to 20
            seen: set[str] = set()
            out: List[str] = []
            for q in queries:
                if q not in seen:
                    seen.add(q)
                    out.append(q)
                    if len(out) >= 20:
                        break
            return out
        except Exception as exc:
            logger.warning(f"Query suggestion failed, returning empty list: {exc}")
            return []
