"""Wrapper around Weaviate v4 client."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import weaviate
from weaviate.classes.config import Property, PropertyType
from weaviate.classes.init import Auth
from weaviate.collections import Collection

from app.config import get_settings
from app.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class WeaviateService:
    """Manage Weaviate schema and vector operations."""

    def __init__(self) -> None:
        self._client = self._create_client()
        self._collection_name = "ProductComment"
        self._ensure_schema()

    def _create_client(self):
        from urllib.parse import urlparse

        endpoint = settings.weaviate_endpoint.rstrip("/")
        parsed = urlparse(endpoint if "://" in endpoint else f"https://{endpoint}")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        return weaviate.connect_to_custom(
            http_host=parsed.hostname or endpoint,
            http_port=port,
            http_secure=parsed.scheme == "https",
            auth_credentials=Auth.api_key(settings.weaviate_api_key),
        )

    def _ensure_schema(self) -> None:
        if self._collection_name in self._client.collections.list_all():
            return
        logger.info("Creating Weaviate collection", collection=self._collection_name)
        self._client.collections.create(
            name=self._collection_name,
            properties=[
                Property(name="product", data_type=PropertyType.TEXT),
                Property(name="platform", data_type=PropertyType.TEXT),
                Property(name="sentiment", data_type=PropertyType.TEXT),
                Property(name="aspects", data_type=PropertyType.TEXT_ARRAY),
            ],
        )

    @property
    def collection(self) -> Collection:
        return self._client.collections.get(self._collection_name)

    def upsert_comment(self, *, uuid: Optional[str], vector: List[float], metadata: Dict[str, Any]) -> str:
        collection = self.collection
        if uuid:
            collection.data.update(uuid=uuid, properties=metadata, vector=vector)
            return uuid
        result = collection.data.insert(properties=metadata, vector=vector)
        return str(result)

    def semantic_search(self, query_vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        response = self.collection.query.near_vector(vector=query_vector, limit=limit)
        results = []
        for obj in response.objects:
            results.append(
                {
                    "uuid": obj.uuid,
                    "score": obj.distance,
                    "properties": obj.properties,
                }
            )
        return results
