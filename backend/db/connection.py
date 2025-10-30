from __future__ import annotations

import os
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable not set")
    if not url.startswith("postgresql+psycopg"):
        raise RuntimeError("Expected asynchronous psycopg URL, got %s" % url)
    return url


def create_engine() -> AsyncEngine:
    return create_async_engine(get_database_url(), future=True, echo=False)


def create_session_factory(engine: AsyncEngine) -> sessionmaker[AsyncSession]:
    return sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def get_session(engine: AsyncEngine | None = None):
    engine = engine or create_engine()
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        yield session
