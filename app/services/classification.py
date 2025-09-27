"""Classification pipeline."""
from __future__ import annotations

from typing import Iterable, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Comment
from app.db.session import get_session
from app.logging import get_logger
from app.services.embeddings import EmbeddingService
from app.services.sentiment import SentimentService
from app.services.weaviate_client import WeaviateService

logger = get_logger(__name__)


class ClassificationService:
    """Classify comments and sync to vector store."""

    def __init__(self) -> None:
        self._sentiment = SentimentService()
        self._embeddings = EmbeddingService()
        self._weaviate = WeaviateService()

    async def run_pending(self, comment_ids: Iterable[int] | None = None) -> None:
        with get_session() as session:
            comments = self._load_comments(session, comment_ids)
            if not comments:
                logger.info("No comments pending classification")
                return
            bodies = [comment.body for comment in comments]
            try:
                sentiments = await self._sentiment.classify(bodies)
            except Exception as exc:
                logger.warning("OpenAI sentiment failed; using fallback", error=str(exc))
                sentiments = self._sentiment.fallback(bodies)
            embeddings = await self._embeddings.embed(bodies)
            for comment, sentiment, vector in zip(comments, sentiments, embeddings):
                comment.sentiment = sentiment["sentiment"]
                comment.sentiment_confidence = int(sentiment["confidence"] * 100)
                comment.aspects = sentiment.get("aspects", {})
                metadata = {
                    "comment_id": comment.id,
                    "product": comment.product,
                    "platform": comment.platform,
                    "sentiment": comment.sentiment,
                    "aspects": list(comment.aspects.keys()) if comment.aspects else [],
                    "text": comment.body,
                }
                weaviate_uuid = self._weaviate.upsert_comment(
                    uuid=comment.weaviate_uuid,
                    vector=vector,
                    metadata=metadata,
                )
                comment.weaviate_uuid = weaviate_uuid
                comment.processed = True
            session.flush()

    def _load_comments(self, session: Session, comment_ids: Iterable[int] | None) -> List[Comment]:
        stmt = select(Comment).where(Comment.processed.is_(False))
        if comment_ids:
            stmt = stmt.where(Comment.id.in_(list(comment_ids)))
        return list(session.execute(stmt).scalars())
