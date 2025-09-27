"""Channel discovery logic for Reddit only (YouTube disabled)."""
from __future__ import annotations

from typing import Dict, List

import asyncpraw

from app.config import get_settings
from app.logging import get_logger
from app.utils import backoff
from app.services.alias_helper import AliasHelper

logger = get_logger(__name__)
settings = get_settings()


class ChannelDiscoveryService:
    """Discover relevant channels/subreddits for products."""

    def __init__(self) -> None:
        self._reddit = asyncpraw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
        )
        logger.info(f"Reddit client initialized with user_agent='{settings.reddit_user_agent}'")

    async def discover_reddit(self, products: List[str]) -> List[Dict[str, object]]:
        """Combine suggested-subreddit measurement and suggested-query search.

        You can comment out either helper call below and still get ranked results
        from the remaining strategy.
        """

        logger.info(f"Starting Reddit discovery for products: {products}")

        # Strategy A: measure OpenAI-suggested subreddits
        a_results = await self._reddit_from_suggested_subreddits(products)

        # Strategy B: run OpenAI-suggested query strings
        b_results = await self._reddit_from_suggested_queries(products)

        merged: Dict[str, Dict[str, object]] = {}
        for item in a_results:
            merged[item["channel_id"]] = item
        for item in b_results:
            cid = item["channel_id"]
            if cid not in merged or item.get("score", 0) > merged[cid].get("score", 0):
                merged[cid] = item

        ranked = sorted(merged.values(), key=lambda it: it.get("score", 0), reverse=True)
        preview = [
            {
                "channel_id": r.get("channel_id"),
                "score": r.get("score"),
                "mentions": r.get("metrics", {}).get("mentions", 0),
            }
            for r in ranked[:5]
        ]
        logger.info(f"Reddit discovery merged preview (up to 5): {preview}")
        return ranked[:20]

    async def _reddit_from_suggested_subreddits(self, products: List[str]) -> List[Dict[str, object]]:
        """Use OpenAI to suggest subreddit names, then measure recent activity."""
        suggested: List[str] = []
        try:
            alias_helper = AliasHelper()
            suggested = await alias_helper.suggest_subreddits(products)
        except Exception as exc:  # pragma: no cover
            logger.warning(f"Suggest_subreddits failed: {exc}")
        if not suggested:
            return []
        logger.info(f"Measuring {len(suggested)} suggested subreddits")
        return await self.measure_subreddits(suggested)

    async def _reddit_from_suggested_queries(self, products: List[str]) -> List[Dict[str, object]]:
        """Use OpenAI to suggest Reddit queries, run them, and rank by subreddit activity."""
        queries: List[str] = []
        try:
            alias_helper = AliasHelper()
            queries = await alias_helper.suggest_reddit_queries(products)
        except Exception as exc:  # pragma: no cover
            logger.warning(f"Suggest_reddit_queries failed: {exc}")
        if not queries:
            return []

        aggregated: Dict[str, Dict[str, object]] = {}
        for q in queries[:5]:  # limit cost/requests
            try:
                subreddit = await self._reddit.subreddit("all")
                async for submission in subreddit.search(q, sort="new", limit=80, time_filter="week"):
                    sub = submission.subreddit.display_name
                    data = aggregated.setdefault(
                        sub,
                        {
                            "platform": "reddit",
                            "channel_id": sub,
                            "name": f"r/{sub}",
                            "metrics": {"mentions": 0, "avg_score": 0.0, "comments": 0},
                        },
                    )
                    metrics = data["metrics"]
                    metrics["mentions"] += 1  # type: ignore[index]
                    metrics["avg_score"] += getattr(submission, "score", 0)  # type: ignore[index]
                    metrics["comments"] += getattr(submission, "num_comments", 0)  # type: ignore[index]
            except Exception as exc:  # pragma: no cover
                logger.warning(f"Query '{q}' search failed: {exc}")

        results: List[Dict[str, object]] = []
        for item in aggregated.values():
            metrics = item["metrics"]
            mentions = max(metrics["mentions"], 1)  # type: ignore[index]
            metrics["avg_score"] = metrics["avg_score"] / mentions  # type: ignore[index]
            item["score"] = float(
                metrics["mentions"] * 0.6
                + metrics["avg_score"] * 0.2
                + metrics["comments"] * 0.2
            )  # type: ignore[index]
            results.append(item)

        return sorted(results, key=lambda it: it.get("score", 0), reverse=True)[:20]

    async def measure_subreddits(self, subreddit_names: List[str], per_sub_limit: int = 20) -> List[Dict[str, object]]:
        """Return metrics for a given list of subreddit names using their recent posts.

        This does not perform keyword search; it only measures recent activity to ensure
        suggested subreddits can surface even if the keyword query missed them.
        """
        results: Dict[str, Dict[str, object]] = {}

        def accumulate(name: str, submission) -> None:
            data = results.setdefault(
                name,
                {
                    "platform": "reddit",
                    "channel_id": name,
                    "name": f"r/{name}",
                    "metrics": {"mentions": 0, "avg_score": 0.0, "comments": 0},
                },
            )
            metrics = data["metrics"]
            metrics["mentions"] += 1  # type: ignore[index]
            metrics["avg_score"] += getattr(submission, "score", 0)  # type: ignore[index]
            metrics["comments"] += getattr(submission, "num_comments", 0)  # type: ignore[index]

        for name in (subreddit_names or [])[:20]:
            try:
                subreddit = await self._reddit.subreddit(name)
                async for submission in subreddit.new(limit=per_sub_limit):
                    accumulate(name, submission)
            except Exception as exc:  # pragma: no cover - network variability
                logger.warning(f"Failed to measure subreddit '{name}': {exc}")

        for _, data in results.items():
            metrics = data["metrics"]
            mentions = max(metrics["mentions"], 1)  # type: ignore[index]
            metrics["avg_score"] = metrics["avg_score"] / mentions  # type: ignore[index]
            data["score"] = float(
                metrics["mentions"] * 0.6
                + metrics["avg_score"] * 0.2
                + metrics["comments"] * 0.2
            )  # type: ignore[index]

        ranked = sorted(results.values(), key=lambda item: item.get("score", 0), reverse=True)
        return ranked[:20]

    # Orchestrator: decide which platform discoverers to call
    async def discover(self, products: List[str]) -> Dict[str, List[Dict[str, object]]]:
        sources: Dict[str, List[Dict[str, object]]] = {}
        # For now only Reddit; future: if settings.youtube_api_key: sources["youtube"] = self.discover_youtube(...)
        sources["reddit"] = await self.discover_reddit(products)
        return sources
