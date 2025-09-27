"""Logging configuration using loguru."""
from __future__ import annotations

import sys
from loguru import logger


def configure_logging() -> None:
    """Configure loguru logger with structured output."""

    logger.remove()
    logger.add(
        sys.stderr,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
        serialize=False,
        level="INFO",
    )


def get_logger(name: str):
    configure_logging()
    return logger.bind(component=name)
