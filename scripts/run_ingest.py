"""CLI utility to trigger ingestion workflow."""
from __future__ import annotations

import asyncio

from app.main import get_app
from app.services.ingestion import IngestionService


async def main() -> None:
    app = get_app()
    ingestion: IngestionService = app.state.services.ingestion  # type: ignore[attr-defined]
    await ingestion.run_once()


if __name__ == "__main__":
    asyncio.run(main())
