from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.models import Fight, Fighter, fighter_stats
from backend.schemas.fighter import FighterDetail, FighterListItem, FightHistoryEntry


class PostgreSQLFighterRepository:
    """Repository for fighter data using PostgreSQL database."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_fighters(
        self, limit: int | None = None, offset: int | None = None
    ) -> Iterable[FighterListItem]:
        """List all fighters with optional pagination."""
        query = select(Fighter)

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        result = await self._session.execute(query)
        fighters = result.scalars().all()

        return [
            FighterListItem(
                fighter_id=fighter.id,
                detail_url=f"http://www.ufcstats.com/fighter-details/{fighter.id}",
                name=fighter.name,
                nickname=fighter.nickname,
                division=fighter.division,
                height=fighter.height,
                weight=fighter.weight,
                reach=fighter.reach,
                stance=fighter.stance,
                dob=fighter.dob,
            )
            for fighter in fighters
        ]

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Get detailed fighter information by ID."""
        query = (
            select(Fighter)
            .where(Fighter.id == fighter_id)
            .options(selectinload(Fighter.fights))
        )
        result = await self._session.execute(query)
        fighter = result.scalar_one_or_none()

        if fighter is None:
            return None

        stats_result = await self._session.execute(
            select(
                fighter_stats.c.category,
                fighter_stats.c.metric,
                fighter_stats.c.value,
            ).where(fighter_stats.c.fighter_id == fighter_id)
        )
        stats_map: dict[str, dict[str, str]] = {}
        for category, metric, value in stats_result.all():
            if category is None or metric is None:
                continue
            category_stats = stats_map.setdefault(category, {})
            category_stats[metric] = value

        # Convert fights to FightHistoryEntry
        fight_history = [
            FightHistoryEntry(
                fight_id=fight.id,
                event_name=fight.event_name,
                event_date=fight.event_date,
                opponent=fight.opponent_name,
                opponent_id=fight.opponent_id,
                result=fight.result,
                method=fight.method or "",
                round=fight.round,
                time=fight.time,
                fight_card_url=fight.fight_card_url,
                stats={},  # TODO: Add fight stats if available
            )
            for fight in fighter.fights
        ]

        return FighterDetail(
            fighter_id=fighter.id,
            detail_url=f"http://www.ufcstats.com/fighter-details/{fighter.id}",
            name=fighter.name,
            nickname=fighter.nickname,
            height=fighter.height,
            weight=fighter.weight,
            reach=fighter.reach,
            stance=fighter.stance,
            dob=fighter.dob,
            record=fighter.record,
            leg_reach=fighter.leg_reach,
            division=fighter.division,
            age=None,  # TODO: Calculate age from dob
            striking=stats_map.get("striking", {}),
            grappling=stats_map.get("grappling", {}),
            significant_strikes=stats_map.get("significant_strikes", {}),
            takedown_stats=stats_map.get("takedown_stats", {}),
            fight_history=fight_history,
        )

    async def stats_summary(self) -> dict[str, float]:
        """Get aggregate statistics about fighters."""
        # Count total fighters
        count_query = select(func.count(Fighter.id))
        result = await self._session.execute(count_query)
        total_fighters = result.scalar() or 0

        return {
            "fighters_indexed": float(total_fighters),
        }

    async def create_fighter(self, fighter: Fighter) -> Fighter:
        """Create a new fighter in the database."""
        self._session.add(fighter)
        await self._session.flush()
        return fighter

    async def upsert_fighter(self, fighter_data: dict) -> Fighter:
        """Insert or update a fighter based on ID."""
        fighter_id = fighter_data.get("id")

        # Check if fighter exists
        query = select(Fighter).where(Fighter.id == fighter_id)
        result = await self._session.execute(query)
        existing_fighter = result.scalar_one_or_none()

        if existing_fighter:
            # Update existing fighter
            for key, value in fighter_data.items():
                if hasattr(existing_fighter, key):
                    setattr(existing_fighter, key, value)
            await self._session.flush()
            return existing_fighter
        else:
            # Create new fighter
            fighter = Fighter(**fighter_data)
            self._session.add(fighter)
            await self._session.flush()
            return fighter

    async def create_fight(self, fight: Fight) -> Fight:
        """Create a new fight record in the database."""
        self._session.add(fight)
        await self._session.flush()
        return fight

    async def search_fighters(
        self, query: str | None = None, stance: str | None = None
    ) -> Iterable[FighterListItem]:
        """Search fighters by name or filter by stance."""
        stmt = select(Fighter)

        if query:
            stmt = stmt.where(
                (Fighter.name.ilike(f"%{query}%"))
                | (Fighter.nickname.ilike(f"%{query}%"))
            )

        if stance:
            stmt = stmt.where(Fighter.stance == stance)

        result = await self._session.execute(stmt)
        fighters = result.scalars().all()

        return [
            FighterListItem(
                fighter_id=fighter.id,
                detail_url=f"http://www.ufcstats.com/fighter-details/{fighter.id}",
                name=fighter.name,
                nickname=fighter.nickname,
                height=fighter.height,
                weight=fighter.weight,
                reach=fighter.reach,
                stance=fighter.stance,
                dob=fighter.dob,
                division=fighter.division,
            )
            for fighter in fighters
        ]

    async def count_fighters(self) -> int:
        """Get the total count of fighters in the database."""
        query = select(func.count()).select_from(Fighter)
        result = await self._session.execute(query)
        return result.scalar_one()

    async def get_random_fighter(self) -> FighterListItem | None:
        """Get a random fighter from the database."""
        query = select(Fighter).order_by(func.random()).limit(1)
        result = await self._session.execute(query)
        fighter = result.scalar_one_or_none()

        if fighter is None:
            return None

        return FighterListItem(
            fighter_id=fighter.id,
            detail_url=f"http://www.ufcstats.com/fighter-details/{fighter.id}",
            name=fighter.name,
            nickname=fighter.nickname,
            division=fighter.division,
            height=fighter.height,
            weight=fighter.weight,
            reach=fighter.reach,
            stance=fighter.stance,
            dob=fighter.dob,
        )
