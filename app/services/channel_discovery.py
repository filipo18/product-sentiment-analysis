"""Channel discovery logic for Reddit and YouTube."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

import praw
from googleapiclient.discovery import build

from app.config import get_settings
from app.logging import get_logger
from app.utils import backoff

logger = get_logger(__name__)
settings = get_settings()


class ChannelDiscoveryService:
    """Discover relevant channels/subreddits for products."""

    def __init__(self) -> None:
        self._reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
        )
        self._youtube = build("youtube", "v3", developerKey=settings.youtube_api_key)

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def discover_reddit(self, products: List[str]) -> List[Dict[str, object]]:
        """Discover subreddits mentioning the products."""

        term = " OR ".join(products)
        results: Dict[str, Dict[str, object]] = {}
        for submission in self._reddit.subreddit("all").search(term, sort="new", limit=200, time_filter="week"):
            subreddit = submission.subreddit.display_name
            data = results.setdefault(
                subreddit,
                {
                    "platform": "reddit",
                    "channel_id": subreddit,
                    "name": f"r/{subreddit}",
                    "metrics": {"mentions": 0, "avg_score": 0.0, "comments": 0},
                },
            )
            metrics = data["metrics"]
            metrics["mentions"] += 1  # type: ignore[index]
            metrics["avg_score"] += submission.score  # type: ignore[index]
            metrics["comments"] += submission.num_comments  # type: ignore[index]
        for subreddit, data in results.items():
            metrics = data["metrics"]
            mentions = max(metrics["mentions"], 1)  # type: ignore[index]
            metrics["avg_score"] = metrics["avg_score"] / mentions  # type: ignore[index]
            data["score"] = float(metrics["mentions"] * 0.6 + metrics["avg_score"] * 0.2 + metrics["comments"] * 0.2)  # type: ignore[index]
        ranked = sorted(results.values(), key=lambda item: item.get("score", 0), reverse=True)
        return ranked[:20]

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def discover_youtube(self, products: List[str]) -> List[Dict[str, object]]:
        """Discover YouTube channels in last 14 days."""

        published_after = (datetime.utcnow() - timedelta(days=14)).isoformat("T") + "Z"
        query = " OR ".join(products)
        search_response = (
            self._youtube.search()
            .list(q=query, part="snippet", maxResults=50, type="video", publishedAfter=published_after)
            .execute()
        )
        channel_stats: Dict[str, Dict[str, object]] = {}
        for item in search_response.get("items", []):
            snippet = item["snippet"]
            channel_id = snippet["channelId"]
            channel = channel_stats.setdefault(
                channel_id,
                {
                    "platform": "youtube",
                    "channel_id": channel_id,
                    "name": snippet.get("channelTitle", "Unknown"),
                    "metrics": {"mentions": 0, "views": 0, "comments": 0},
                },
            )
            channel["metrics"]["mentions"] += 1  # type: ignore[index]

        if channel_stats:
            channels = list(channel_stats.keys())
            stats_response = (
                self._youtube.channels().list(id=",".join(channels), part="statistics").execute()
            )
            for channel in stats_response.get("items", []):
                cid = channel["id"]
                metrics = channel_stats[cid]["metrics"]
                stats = channel["statistics"]
                metrics["views"] = int(stats.get("viewCount", 0))
                metrics["comments"] = int(stats.get("commentCount", 0))
                channel_stats[cid]["score"] = float(
                    metrics["mentions"] * 0.5 + metrics["views"] * 0.0001 + metrics["comments"] * 0.2
                )
        ranked = sorted(channel_stats.values(), key=lambda item: item.get("score", 0), reverse=True)
        return ranked[:20]

    def discover(self, products: List[str]) -> Dict[str, List[Dict[str, object]]]:
        return {
            "reddit": self.discover_reddit(products),
            "youtube": self.discover_youtube(products),
        }
