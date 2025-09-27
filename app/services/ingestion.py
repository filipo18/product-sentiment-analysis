"""Ingestion service orchestrating Reddit and YouTube pulls."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List

import praw
from googleapiclient.discovery import build
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Comment, ContentItem, SourceChannel
from app.db.session import get_session
from app.logging import get_logger
from app.utils import backoff
from app.utils.text import normalize_text

logger = get_logger(__name__)
settings = get_settings()


class IngestionService:
    """Ingest content from configured sources."""

    def __init__(self) -> None:
        self._reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
        )
        self._youtube = build("youtube", "v3", developerKey=settings.youtube_api_key)

    async def run_once(self, products: Iterable[str] | None = None) -> None:
        products = list(products or settings.default_products)
        logger.info("Starting ingestion", products=products)
        await self._ingest_reddit(products)
        await self._ingest_youtube(products)

    async def _ingest_reddit(self, products: List[str]) -> None:
        logger.info("Ingesting Reddit content", products=products)
        with get_session() as session:
            for product in products:
                await self._ingest_reddit_product(session, product)

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def _ingest_reddit_product(self, session: Session, product: str) -> None:
        query = product
        subreddit_names = [channel.channel_id for channel in session.execute(
            select(SourceChannel).where(SourceChannel.platform == "reddit")
        ).scalars()]
        subreddits = "+".join(subreddit_names) if subreddit_names else "all"
        for submission in self._reddit.subreddit(subreddits).search(query, sort="new", limit=50):
            content = self._get_or_create_content(session, submission, product)
            submission.comments.replace_more(limit=None)
            for comment in submission.comments.list():
                self._upsert_comment(session, comment, content, product)

    def _get_or_create_content(self, session: Session, submission, product: str) -> ContentItem:
        existing = session.execute(
            select(ContentItem).where(ContentItem.platform == "reddit", ContentItem.item_id == submission.id)
        ).scalar_one_or_none()
        if existing:
            return existing
        channel = self._get_or_create_source(
            session,
            platform="reddit",
            channel_id=submission.subreddit.display_name,
            name=f"r/{submission.subreddit.display_name}",
            metadata={"subscribers": submission.subreddit.subscribers},
        )
        content = ContentItem(
            platform="reddit",
            item_id=submission.id,
            product=product,
            title=submission.title,
            url=submission.url,
            author=submission.author.name if submission.author else "unknown",
            published_at=datetime.utcfromtimestamp(submission.created_utc),
            score=submission.score,
            metadata={"num_comments": submission.num_comments},
            source=channel,
        )
        session.add(content)
        session.flush()
        return content

    def _upsert_comment(self, session: Session, comment, content: ContentItem, product: str) -> None:
        existing = session.execute(
            select(Comment).where(Comment.platform == "reddit", Comment.comment_id == comment.id)
        ).scalar_one_or_none()
        if existing:
            return
        normalized_body = normalize_text(comment.body or "")
        record = Comment(
            platform="reddit",
            comment_id=comment.id,
            product=product,
            author=comment.author.name if comment.author else "unknown",
            body=normalized_body,
            parent_id=str(comment.parent_id),
            published_at=datetime.utcfromtimestamp(comment.created_utc),
            score=getattr(comment, "score", 0),
            metadata={"permalink": comment.permalink},
            content=content,
        )
        session.add(record)

    async def _ingest_youtube(self, products: List[str]) -> None:
        logger.info("Ingesting YouTube content", products=products)
        with get_session() as session:
            for product in products:
                await self._ingest_youtube_product(session, product)

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def _ingest_youtube_product(self, session: Session, product: str) -> None:
        channels = [channel.channel_id for channel in session.execute(
            select(SourceChannel).where(SourceChannel.platform == "youtube")
        ).scalars()]
        query = product
        search = (
            self._youtube.search()
            .list(q=query, part="id,snippet", maxResults=25, type="video", order="date")
            .execute()
        )
        for item in search.get("items", []):
            video_id = item["id"]["videoId"]
            channel_id = item["snippet"]["channelId"]
            if channels and channel_id not in channels:
                continue
            video = self._youtube.videos().list(id=video_id, part="snippet,statistics").execute()
            if not video.get("items"):
                continue
            details = video["items"][0]
            content = self._get_or_create_youtube_content(session, details, product)
            self._ingest_youtube_comments(session, video_id, content, product)

    def _get_or_create_source(self, session: Session, platform: str, channel_id: str, name: str, metadata: Dict[str, object]) -> SourceChannel:
        existing = session.execute(
            select(SourceChannel).where(SourceChannel.platform == platform, SourceChannel.channel_id == channel_id)
        ).scalar_one_or_none()
        if existing:
            return existing
        source = SourceChannel(platform=platform, channel_id=channel_id, name=name, metadata=metadata)
        session.add(source)
        session.flush()
        return source

    def _get_or_create_youtube_content(self, session: Session, video: Dict[str, object], product: str) -> ContentItem:
        video_id = video["id"]
        existing = session.execute(
            select(ContentItem).where(ContentItem.platform == "youtube", ContentItem.item_id == video_id)
        ).scalar_one_or_none()
        if existing:
            return existing
        snippet = video["snippet"]
        stats = video["statistics"]
        channel = self._get_or_create_source(
            session,
            platform="youtube",
            channel_id=snippet["channelId"],
            name=snippet.get("channelTitle", "Unknown"),
            metadata={"viewCount": stats.get("viewCount", 0)},
        )
        content = ContentItem(
            platform="youtube",
            item_id=video_id,
            product=product,
            title=snippet.get("title", ""),
            url=f"https://www.youtube.com/watch?v={video_id}",
            author=snippet.get("channelTitle"),
            published_at=datetime.strptime(snippet["publishedAt"], "%Y-%m-%dT%H:%M:%SZ"),
            score=int(stats.get("likeCount", 0)),
            metadata={"viewCount": stats.get("viewCount", 0)},
            source=channel,
        )
        session.add(content)
        session.flush()
        return content

    def _ingest_youtube_comments(self, session: Session, video_id: str, content: ContentItem, product: str) -> None:
        request = self._youtube.commentThreads().list(
            part="snippet,replies", videoId=video_id, maxResults=50, textFormat="plainText"
        )
        while request:
            response = request.execute()
            for item in response.get("items", []):
                top_comment = item["snippet"]["topLevelComment"]
                self._upsert_youtube_comment(session, top_comment, content, product)
                for reply in item.get("replies", {}).get("comments", []):
                    self._upsert_youtube_comment(session, reply, content, product)
            request = self._youtube.commentThreads().list_next(request, response)

    def _upsert_youtube_comment(self, session: Session, comment_payload: Dict[str, object], content: ContentItem, product: str) -> None:
        snippet = comment_payload["snippet"]
        comment_id = comment_payload["id"]
        existing = session.execute(
            select(Comment).where(Comment.platform == "youtube", Comment.comment_id == comment_id)
        ).scalar_one_or_none()
        if existing:
            return
        normalized_body = normalize_text(snippet.get("textDisplay", ""))
        record = Comment(
            platform="youtube",
            comment_id=comment_id,
            product=product,
            author=snippet.get("authorDisplayName"),
            body=normalized_body,
            parent_id=snippet.get("parentId"),
            published_at=datetime.strptime(snippet["publishedAt"], "%Y-%m-%dT%H:%M:%SZ"),
            score=int(snippet.get("likeCount", 0)),
            metadata={"videoId": snippet.get("videoId")},
            content=content,
        )
        session.add(record)
