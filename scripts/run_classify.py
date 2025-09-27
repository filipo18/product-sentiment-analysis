"""CLI utility to trigger classification pipeline."""
from __future__ import annotations

import asyncio

from app.main import get_app
from app.services.classification import ClassificationService


async def main() -> None:
    app = get_app()
    classifier: ClassificationService = app.state.services.classifier  # type: ignore[attr-defined]
    await classifier.run_pending()


if __name__ == "__main__":
    asyncio.run(main())
