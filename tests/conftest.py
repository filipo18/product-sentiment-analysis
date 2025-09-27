import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Provide default environment variables for settings
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("REDDIT_CLIENT_ID", "test")
os.environ.setdefault("REDDIT_CLIENT_SECRET", "test")
os.environ.setdefault("REDDIT_USER_AGENT", "test")
os.environ.setdefault("YOUTUBE_API_KEY", "test")
os.environ.setdefault("WEAVIATE_ENDPOINT", "http://localhost")
os.environ.setdefault("WEAVIATE_API_KEY", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
