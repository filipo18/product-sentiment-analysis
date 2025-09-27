"""Shared Pydantic models."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ProductInput(BaseModel):
    products: List[str] = Field(..., min_items=1)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class DiscoverResponse(BaseModel):
    platform: str
    channel_id: str
    name: str
    score: float
    metrics: Dict[str, float]


class IngestRequest(BaseModel):
    products: List[str]
    sources: List[str]
    poll_interval: Optional[int] = None


class ClassificationRequest(BaseModel):
    comment_ids: List[int]


class SentimentResult(BaseModel):
    sentiment: str
    confidence: float
    aspects: Dict[str, str]


class SummaryResponse(BaseModel):
    product: str
    overall: str
    delights: List[str]
    pain_points: List[str]


class SearchResponse(BaseModel):
    comment_id: int
    product: str
    text: str
    score: float
    metadata: Dict[str, str]
