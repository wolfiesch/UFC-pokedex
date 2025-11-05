#!/usr/bin/env python
"""Initialize database tables."""
import asyncio

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from backend.db.connection import create_engine
from backend.db.models import Base


async def init_db():
    engine = create_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("✓ Database tables created successfully")

if __name__ == "__main__":
    asyncio.run(init_db())
