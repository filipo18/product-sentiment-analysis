"""FastAPI application entry point."""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging import configure_logging, get_logger
from app.models.common import (
    ClassificationRequest,
    DiscoverResponse,
    IngestRequest,
    ProductInput,
    SearchResponse,
    SummaryResponse,
)
from app.services.alias_helper import AliasHelper
from app.services.channel_discovery import ChannelDiscoveryService
from app.services.classification import ClassificationService
from app.services.ingestion import IngestionService
from app.services.metrics import MetricsService
from app.services.search import SearchService
from app.services.summarizer import SummaryService
from app.services.weaviate_client import WeaviateService

configure_logging()
logger = get_logger(__name__)


class ServiceRegistry:
    def __init__(self) -> None:
        self.alias_helper = AliasHelper()
        self.discovery = ChannelDiscoveryService()
        self.ingestion = IngestionService()
        self.classifier = ClassificationService()
        self.metrics = MetricsService()
        self.summarizer = SummaryService()
        self.search = SearchService()
        self.weaviate = WeaviateService()


def get_services() -> ServiceRegistry:
    return app.state.services  # type: ignore[attr-defined]


settings = get_settings()
app = FastAPI(title="Product Social Sensing API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"]
    ,
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting application")
    app.state.services = ServiceRegistry()  # type: ignore[attr-defined]


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Shutting down application")


def get_product_input(payload: ProductInput) -> ProductInput:
    products = [p.strip() for p in payload.products if p.strip()]
    if not products:
        raise HTTPException(status_code=400, detail="At least one product required")
    payload.products = products
    return payload


@app.post("/discover", response_model=Dict[str, List[DiscoverResponse]])
async def discover_products(
    payload: ProductInput,
    services: ServiceRegistry = Depends(get_services),
) -> Dict[str, List[DiscoverResponse]]:
    input_payload = get_product_input(payload)
    aliases = await services.alias_helper.generate_aliases(input_payload.products)
    flattened_terms = sorted({alias for terms in aliases.values() for alias in terms})
    discovery = services.discovery.discover(flattened_terms)
    return {
        platform: [DiscoverResponse(**item) for item in items]
        for platform, items in discovery.items()
    }


@app.post("/ingest")
async def ingest_sources(
    payload: IngestRequest,
    services: ServiceRegistry = Depends(get_services),
) -> Dict[str, Any]:
    products = payload.products or settings.default_products
    await services.ingestion.run_once(products)
    return {"status": "queued", "products": products}


@app.post("/classify")
async def classify_comments(
    payload: ClassificationRequest,
    services: ServiceRegistry = Depends(get_services),
) -> Dict[str, str]:
    await services.classifier.run_pending(payload.comment_ids)
    return {"status": "completed"}


@app.get("/metrics")
async def get_metrics(
    products: List[str] | None = None,
    services: ServiceRegistry = Depends(get_services),
) -> Dict[str, Any]:
    return {
        "sentiment": services.metrics.sentiment_distribution(products),
        "voice_share": services.metrics.voice_share(products),
        "aspects": services.metrics.aspect_sentiment(products),
        "comparatives": services.metrics.comparatives(),
    }


@app.get("/summary", response_model=List[SummaryResponse])
async def get_summary(
    products: List[str] | None = None,
    services: ServiceRegistry = Depends(get_services),
) -> List[SummaryResponse]:
    if not products:
        products = settings.default_products
    summaries: List[SummaryResponse] = []
    for product in products:
        # in MVP, fetch last N comments from DB
        from sqlalchemy import select

        from app.db.models import Comment
        from app.db.session import get_session

        with get_session() as session:
            rows = (
                session.execute(
                    select(Comment.body)
                    .where(Comment.product == product)
                    .order_by(Comment.published_at.desc())
                    .limit(200)
                )
                .scalars()
                .all()
            )
        if not rows:
            continue
        summary = await services.summarizer.summarize(product, list(rows))
        summaries.append(SummaryResponse(product=product, **summary))
    return summaries


@app.get("/search", response_model=List[SearchResponse])
async def semantic_search(
    query: str,
    limit: int = 5,
    services: ServiceRegistry = Depends(get_services),
) -> List[SearchResponse]:
    results = await services.search.search(query, limit)
    return [
        SearchResponse(
            comment_id=result["properties"].get("comment_id", 0),
            product=result["properties"].get("product", ""),
            text=result["properties"].get("text", ""),
            score=result.get("score", 0.0),
            metadata=result["properties"],
        )
        for result in results
    ]


@app.get("/news/seed")
async def seed_news_terms(products: List[str] | None = None) -> Dict[str, Any]:
    products = products or settings.default_products
    seeds = [f"{product} launch" for product in products]
    return {"providers": [], "seeds": seeds}


@app.get("/health")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}


def get_app() -> FastAPI:
    return app
