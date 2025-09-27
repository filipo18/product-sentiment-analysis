"""Configuration management using Pydantic settings."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional, Type

try:  # pragma: no cover - prefer real dependency
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover - lightweight fallback

    class SettingsConfigDict(dict):
        pass

    class BaseSettings:
        model_config: Optional[SettingsConfigDict] = None

        def __init__(self, **kwargs):
            for field, field_type in self.__annotations__.items():
                env_key = field.upper()
                value = kwargs.get(field)
                if value is None and env_key in os.environ:
                    value = os.environ[env_key]
                if value is None:
                    value = getattr(self, field, None)
                if value is None:
                    raise RuntimeError(f"Missing environment variable: {env_key}")
                setattr(self, field, self._cast_value(value, field_type))

        @staticmethod
        def _cast_value(value, field_type: Type):
            origin = getattr(field_type, "__origin__", None)
            if origin is list or origin is List:
                if isinstance(value, str):
                    return [item.strip() for item in value.split(",") if item.strip()]
                return list(value)
            if field_type is bool:
                return str(value).lower() in {"1", "true", "yes"}
            if field_type in (int, float):
                return field_type(value)
            return value


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    openai_api_key: str
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str
    youtube_api_key: str
    weaviate_endpoint: str
    weaviate_api_key: str
    database_url: str

    openai_model_sentiment: str = "gpt-5-mini"
    openai_model_summary: str = "gpt-5"
    openai_embedding_model: str = "text-embedding-3-large"

    poll_interval_seconds: int = 900
    default_products: List[str] = ["iPhone 16", "iPhone 17"]
    lightpanda_enabled: bool = False

    model_config = SettingsConfigDict(env_file=(".env",), extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    settings = Settings()
    return settings
