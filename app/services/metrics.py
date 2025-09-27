"""Analytics calculations."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, Iterable

from sqlalchemy import func, select

from app.db.models import Comment, ContentItem
from app.db.session import get_session


class MetricsService:
    """Generate analytics for dashboard and APIs."""

    def sentiment_distribution(self, products: Iterable[str] | None = None) -> Dict[str, Dict[str, int]]:
        with get_session() as session:
            stmt = select(Comment.product, Comment.platform, Comment.sentiment, func.count(Comment.id)).group_by(
                Comment.product, Comment.platform, Comment.sentiment
            )
            if products:
                stmt = stmt.where(Comment.product.in_(list(products)))
            rows = session.execute(stmt).all()
        data: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for product, platform, sentiment, count in rows:
            key = f"{product}:{platform}"
            data[key][sentiment or "unknown"] += count
        return {k: dict(v) for k, v in data.items()}

    def voice_share(self, products: Iterable[str] | None = None) -> Dict[str, int]:
        with get_session() as session:
            stmt = select(Comment.platform, func.count(Comment.id)).group_by(Comment.platform)
            if products:
                stmt = stmt.where(Comment.product.in_(list(products)))
            rows = session.execute(stmt).all()
        return {platform: count for platform, count in rows}

    def aspect_sentiment(self, products: Iterable[str] | None = None) -> Dict[str, Dict[str, Counter]]:
        with get_session() as session:
            stmt = select(Comment.product, Comment.platform, Comment.aspects, Comment.sentiment)
            if products:
                stmt = stmt.where(Comment.product.in_(list(products)))
            rows = session.execute(stmt).all()
        result: Dict[str, Dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
        for product, platform, aspects, sentiment in rows:
            aspects = aspects or {}
            for aspect in aspects.keys():
                result[product][aspect][sentiment or "unknown"] += 1
        return {product: {aspect: dict(counter) for aspect, counter in aspects.items()} for product, aspects in result.items()}

    def comparatives(self) -> Dict[str, Dict[str, int]]:
        with get_session() as session:
            stmt = select(ContentItem.product, func.count(ContentItem.id)).group_by(ContentItem.product)
            rows = session.execute(stmt).all()
        return {product: count for product, count in rows}
