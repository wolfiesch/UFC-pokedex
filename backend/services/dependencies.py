"""FastAPI dependency wiring for backend services.

Separating dependency factories from service implementation modules keeps the
latter free of web-layer concerns, enabling easier reuse in tests and other
consumers (e.g. CLI utilities).
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import CacheClient, get_cache_client
from backend.db.connection import get_db
from backend.db.repositories.fighter_repository import FighterRepository
from backend.db.repositories.odds import OddsRepository
from backend.services.fighter_query_service import FighterQueryService
from backend.services.odds_query_service import OddsQueryService


def get_fighter_query_service(
    session: AsyncSession = Depends(get_db),
    cache: CacheClient = Depends(get_cache_client),
) -> FighterQueryService:
    """Provide a fully-wired :class:`FighterQueryService` instance.

    The dependency is intentionally thin and only resolves infrastructure
    dependencies (database session + cache) before instantiating the service.
    Keeping this logic here avoids circular imports between FastAPI routers and
    the service modules themselves.
    """

    repository = FighterRepository(session)
    return FighterQueryService(repository, cache=cache)


def get_odds_query_service(
    session: AsyncSession = Depends(get_db),
    cache: CacheClient = Depends(get_cache_client),
) -> OddsQueryService:
    """Wire repository + cache dependencies for the odds service."""

    repository = OddsRepository(session)
    return OddsQueryService(repository, cache=cache)


__all__ = ["get_fighter_query_service", "get_odds_query_service"]
