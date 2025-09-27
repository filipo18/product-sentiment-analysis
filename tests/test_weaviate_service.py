import os
from unittest.mock import MagicMock

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("REDDIT_CLIENT_ID", "test")
os.environ.setdefault("REDDIT_CLIENT_SECRET", "test")
os.environ.setdefault("REDDIT_USER_AGENT", "test")
os.environ.setdefault("YOUTUBE_API_KEY", "test")
os.environ.setdefault("WEAVIATE_ENDPOINT", "http://localhost")
os.environ.setdefault("WEAVIATE_API_KEY", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import pytest

weaviate = pytest.importorskip("weaviate")

from app.services.weaviate_client import WeaviateService


def _mock_client(monkeypatch):
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.collections.list_all.return_value = ["ProductComment"]
    mock_client.collections.get.return_value = mock_collection
    monkeypatch.setattr(weaviate, "connect_to_custom", lambda *args, **kwargs: mock_client)
    return mock_client, mock_collection


def test_upsert_comment_updates_existing(monkeypatch):
    mock_client, mock_collection = _mock_client(monkeypatch)

    service = WeaviateService()
    service.upsert_comment(uuid="123", vector=[0.1, 0.2], metadata={"product": "test"})
    mock_collection.data.update.assert_called_once()


def test_semantic_search(monkeypatch):
    mock_client, mock_collection = _mock_client(monkeypatch)
    mock_collection.query.near_vector.return_value.objects = [
        MagicMock(uuid="1", distance=0.1, properties={"product": "test"})
    ]
    service = WeaviateService()
    results = service.semantic_search([0.1, 0.2])
    assert results[0]["properties"]["product"] == "test"
