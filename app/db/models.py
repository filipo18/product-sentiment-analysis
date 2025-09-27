"""Database models."""
from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class SourceChannel(Base):
    __tablename__ = "source_channel"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(20), nullable=False)
    channel_id = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    meta_data = Column(JSONB, nullable=True)
    last_polled_at = Column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("platform", "channel_id", name="uq_platform_channel"),)

    contents = relationship("ContentItem", back_populates="source")


class ContentItem(Base):
    __tablename__ = "content_item"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(20), nullable=False)
    item_id = Column(String(255), nullable=False)
    product = Column(String(255), nullable=False, index=True)
    title = Column(String(512), nullable=False)
    url = Column(String(512), nullable=False)
    author = Column(String(255), nullable=True)
    published_at = Column(DateTime, nullable=False, index=True)
    score = Column(Integer, default=0)
    meta_data = Column(JSONB, nullable=True)
    source_channel_id = Column(Integer, ForeignKey("source_channel.id"), nullable=False)
    embeddings_id = Column(String(255), nullable=True)

    __table_args__ = (UniqueConstraint("platform", "item_id", name="uq_platform_item"),)

    source = relationship("SourceChannel", back_populates="contents")
    comments = relationship("Comment", back_populates="content")


class Comment(Base):
    __tablename__ = "comment"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(20), nullable=False)
    comment_id = Column(String(255), nullable=False)
    product = Column(String(255), nullable=False, index=True)
    author = Column(String(255), nullable=True)
    body = Column(Text, nullable=False)
    parent_id = Column(String(255), nullable=True)
    published_at = Column(DateTime, nullable=False, index=True)
    score = Column(Integer, default=0)
    sentiment = Column(String(20), nullable=True)
    sentiment_confidence = Column(Integer, nullable=True)
    aspects = Column(JSONB, nullable=True)
    summary = Column(Text, nullable=True)
    vector_id = Column(String(255), nullable=True)
    meta_data = Column(JSONB, nullable=True)
    content_item_id = Column(Integer, ForeignKey("content_item.id"), nullable=False)
    weaviate_uuid = Column(String(255), nullable=True)
    processed = Column(Boolean, default=False)

    __table_args__ = (UniqueConstraint("platform", "comment_id", name="uq_platform_comment"),)

    content = relationship("ContentItem", back_populates="comments")


if __name__ == "__main__":  # pragma: no cover - manual invocation
    from app.db.session import _engine

    Base.metadata.create_all(_engine)
