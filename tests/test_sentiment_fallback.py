import os

# Ensure required environment variables exist for settings during import
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("REDDIT_CLIENT_ID", "test")
os.environ.setdefault("REDDIT_CLIENT_SECRET", "test")
os.environ.setdefault("REDDIT_USER_AGENT", "test")
os.environ.setdefault("YOUTUBE_API_KEY", "test")
os.environ.setdefault("WEAVIATE_ENDPOINT", "http://localhost")
os.environ.setdefault("WEAVIATE_API_KEY", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.services.sentiment import SentimentService


def test_vader_fallback_scores():
    service = SentimentService()
    results = service.fallback(["I love this phone", "I hate the battery"])
    assert results[0]["sentiment"] == "positive"
    assert results[1]["sentiment"] == "negative"
