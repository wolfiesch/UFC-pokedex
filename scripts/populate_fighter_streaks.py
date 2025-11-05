#!/usr/bin/env python3
"""
Populate pre-computed streak columns for all fighters.

This script computes current win/loss streaks for all fighters and updates
the current_streak_type and current_streak_count columns in the fighters table.

Usage:
    .venv/bin/python scripts/populate_fighter_streaks.py

Or via make:
    make populate-streaks
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, update

from backend.db.connection import get_session
from backend.db.models import Fighter
from backend.db.repositories import PostgreSQLFighterRepository


async def populate_fighter_streaks():
    """Compute and populate streak data for all fighters."""
    print("=== Populating Fighter Streaks ===\n")

    async with get_session() as session:
        repo = PostgreSQLFighterRepository(session)

        # Step 1: Get all fighter IDs
        print("Step 1: Fetching all fighter IDs...")
        result = await session.execute(select(Fighter.id, Fighter.name))
        fighters = result.all()
        fighter_ids = [f.id for f in fighters]
        total_fighters = len(fighter_ids)
        print(f"Found {total_fighters} fighters to process\n")

        # Step 2: Batch compute streaks for all fighters
        print("Step 2: Computing streaks (this may take a minute)...")
        streaks = await repo._batch_compute_streaks(fighter_ids, window=6)
        print(f"Computed streaks for {len(streaks)} fighters\n")

        # Step 3: Update fighters in batches
        print("Step 3: Updating database...")
        batch_size = 100
        updated_count = 0
        fighters_with_streaks = 0

        for i in range(0, total_fighters, batch_size):
            batch_ids = fighter_ids[i : i + batch_size]

            for fighter_id in batch_ids:
                streak_info = streaks.get(fighter_id, {})
                streak_type = streak_info.get("current_streak_type")
                streak_count = streak_info.get("current_streak_count", 0)

                # Track fighters with active streaks
                if streak_type and streak_count > 0:
                    fighters_with_streaks += 1

                # Update the fighter
                stmt = (
                    update(Fighter)
                    .where(Fighter.id == fighter_id)
                    .values(
                        current_streak_type=streak_type,
                        current_streak_count=streak_count,
                    )
                )
                await session.execute(stmt)
                updated_count += 1

            # Commit this batch
            await session.commit()
            print(
                f"  Processed {min(i + batch_size, total_fighters)}/{total_fighters} "
                f"fighters ({updated_count / total_fighters * 100:.1f}%)"
            )

        print(f"\n=== Streak Population Complete ===")
        print(f"Total fighters updated: {updated_count}")
        print(f"Fighters with active streaks: {fighters_with_streaks}")
        print(
            f"Fighters with no streak: {updated_count - fighters_with_streaks}"
        )

        # Step 4: Show sample streaks
        print(f"\n=== Sample Win Streaks (Top 10) ===")
        result = await session.execute(
            select(Fighter.name, Fighter.current_streak_count, Fighter.record)
            .where(Fighter.current_streak_type == "win")
            .order_by(Fighter.current_streak_count.desc())
            .limit(10)
        )
        for fighter in result.all():
            print(
                f"  {fighter.name}: {fighter.current_streak_count} wins "
                f"(Record: {fighter.record})"
            )

        print(f"\n=== Streak Distribution ===")
        result = await session.execute(
            select(Fighter.current_streak_type)
            .where(Fighter.current_streak_type.isnot(None))
        )
        all_streak_types = result.scalars().all()

        from collections import Counter

        streak_counts = Counter(all_streak_types)
        for streak_type, count in streak_counts.most_common():
            print(f"  {streak_type}: {count} fighters")

        print("\n✅ Streak columns populated successfully!")
        print(
            "\nYou can now use streak filtering in the API:\n"
            "  /search/?q=&streak_type=win&min_streak_count=3"
        )


if __name__ == "__main__":
    asyncio.run(populate_fighter_streaks())
