"""Backoff utility with graceful fallback when dependency is missing."""
from __future__ import annotations

from typing import Any, Callable

try:  # pragma: no cover - real implementation preferred
    import backoff as _backoff
except ImportError:  # pragma: no cover - fallback for test environments

    def expo(*args: Any, **kwargs: Any) -> Callable:
        def wrapper(func: Callable) -> Callable:
            return func

        return wrapper

    def on_exception(*args: Any, **kwargs: Any) -> Callable:
        def decorator(func: Callable) -> Callable:
            return func

        return decorator

else:  # pragma: no cover
    expo = _backoff.expo
    on_exception = _backoff.on_exception
