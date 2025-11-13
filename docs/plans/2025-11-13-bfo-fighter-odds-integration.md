# BFO Fighter Odds Data Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Clean, validate, and integrate 14,054 BFO fighter odds records into the database with proper indexing and API endpoints

**Architecture:** Create new database table for fighter odds history, build data cleaning pipeline to handle duplicates and format normalization, implement repository layer with efficient queries, expose REST API endpoints, and create frontend visualization components

**Tech Stack:**
- Python 3.13 (asyncio, SQLAlchemy)
- PostgreSQL with time-series indexes
- FastAPI for REST endpoints
- Next.js 14 + Recharts for visualization
- Scrapy for future updates

**Data Quality Summary:**
- Total records: 14,054
- Unique fighters: 1,255 / 1,262 (99.4% coverage)
- Duplicates: 216 records (1.5%) - to be removed
- Old format records: 78 (0.6%) - needs normalization
- Missing odds: 17 records (0.1%)
- Usable quality (>10 points): 12,217 (86.9%)

---

## Phase 1: Database Schema & Migration

### Task 1: Create FighterOdds Model

**Files:**
- Create: `backend/db/models/odds.py`
- Modify: `backend/db/models/__init__.py:464-473`

**Step 1: Write the failing test**

```python
# tests/test_models_odds.py
from datetime import datetime
from backend.db.models.odds import FighterOdds, OddsDataPoint


def test_fighter_odds_model_creation():
    """Test basic FighterOdds model instantiation."""
    odds = FighterOdds(
        id="test-odds-id",
        fighter_id="7492",
        opponent_name="Islam Makhachev",
        event_name="UFC 322",
        opening_odds="+275",
        closing_range_start="+210",
        closing_range_end="+230",
        num_odds_points=93
    )
    assert odds.fighter_id == "7492"
    assert odds.opponent_name == "Islam Makhachev"
    assert odds.num_odds_points == 93


def test_odds_data_point_model():
    """Test OddsDataPoint model for time-series data."""
    point = OddsDataPoint(
        timestamp_ms=1753455870000,
        timestamp=datetime.fromisoformat("2025-07-25T15:04:30.000Z"),
        odds=3.75
    )
    assert point.odds == 3.75
    assert point.timestamp_ms == 1753455870000
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_models_odds.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'backend.db.models.odds'"

**Step 3: Write minimal model implementation**

```python
# backend/db/models/odds.py
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base


class FighterOdds(Base):
    """Fighter betting odds history from BestFightOdds."""

    __tablename__ = "fighter_odds"
    __table_args__ = (
        Index("ix_fighter_odds_fighter_id", "fighter_id"),
        Index("ix_fighter_odds_event_date", "event_date"),
        Index("ix_fighter_odds_quality", "data_quality_tier"),
        Index("ix_fighter_odds_fighter_opponent", "fighter_id", "opponent_name"),
        UniqueConstraint(
            "fighter_id",
            "opponent_name",
            "event_name",
            name="uq_fighter_odds_fight"
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    fighter_id: Mapped[str] = mapped_column(
        ForeignKey("fighters.id"),
        nullable=False,
        doc="Foreign key to fighters table"
    )
    opponent_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Opponent name as recorded on BFO"
    )
    event_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Event name from BFO"
    )
    event_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="BFO event page URL"
    )
    event_date: Mapped[datetime | None] = mapped_column(
        Date,
        nullable=True,
        doc="Date of the event"
    )

    # Opening and closing odds
    opening_odds: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        doc="Opening odds (e.g., '+275', '-165')"
    )
    closing_range_start: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        doc="Start of closing odds range"
    )
    closing_range_end: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        doc="End of closing odds range"
    )

    # Time-series odds history
    mean_odds_history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        doc="Array of {timestamp_ms, timestamp, odds} data points"
    )
    num_odds_points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of data points in time series"
    )

    # Data quality metadata
    data_quality_tier: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        doc="Quality tier: 'excellent', 'good', 'usable', 'poor', 'no_data'"
    )
    is_duplicate: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Flagged as duplicate record"
    )

    # Scraping metadata
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        doc="When this data was scraped"
    )
    bfo_fighter_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="BFO fighter page URL for re-scraping"
    )

    # Relationships
    fighter: Mapped["Fighter"] = relationship("Fighter")


# Helper class for type hints (not a DB model)
class OddsDataPoint:
    """Type structure for odds time-series data points."""
    timestamp_ms: int
    timestamp: datetime
    odds: float
```

**Step 4: Update models __init__.py**

```python
# backend/db/models/__init__.py (add to imports and __all__)
from .odds import FighterOdds  # noqa: E402

__all__ = [
    "Base",
    "Event",
    "Fight",
    "Fighter",
    "FighterRanking",
    "FighterOdds",  # Add this
    "FavoriteCollection",
    "FavoriteEntry",
    "fighter_stats",
]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_models_odds.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/db/models/odds.py backend/db/models/__init__.py tests/test_models_odds.py
git commit -m "feat: add FighterOdds database model for BFO odds history

- Create fighter_odds table with time-series JSON column
- Add indexes for fighter_id, event_date, quality tier
- Unique constraint on fighter+opponent+event
- Include data quality and duplicate flags"
```

---

### Task 2: Create Database Migration

**Files:**
- Create: `backend/db/migrations/versions/XXXXX_add_fighter_odds_table.py`

**Step 1: Generate migration with alembic**

Run: `make db-migration MSG="add_fighter_odds_table"`

**Step 2: Review generated migration file**

Expected upgrade():
- Create fighter_odds table with all columns
- Add indexes and constraints
- Add foreign key to fighters table

**Step 3: Test migration (dry run)**

Run: `make db-upgrade-test` (or PostgreSQL EXPLAIN)

**Step 4: Apply migration to development database**

Run: `make db-upgrade`
Expected: Migration applies successfully

**Step 5: Verify table creation**

```bash
PGPASSWORD=ufc_pokedex psql -h localhost -p 5432 -U ufc_pokedex -d ufc_pokedex -c "\d fighter_odds"
```

Expected: Table schema displayed with all columns and indexes

**Step 6: Commit**

```bash
git add backend/db/migrations/versions/*_add_fighter_odds_table.py
git commit -m "migration: create fighter_odds table for BFO data

- Add fighter_odds table with time-series JSON column
- Create indexes for efficient queries
- Foreign key constraint to fighters table"
```

---

## Phase 2: Data Cleaning Pipeline

### Task 3: Create Data Cleaning Script

**Files:**
- Create: `scripts/clean_bfo_fighter_mean_odds.py`
- Create: `tests/test_clean_bfo_odds.py`

**Step 1: Write failing test**

```python
# tests/test_clean_bfo_odds.py
import json
from pathlib import Path
from scripts.clean_bfo_fighter_mean_odds import (
    detect_duplicates,
    normalize_odds_format,
    calculate_quality_tier,
    clean_odds_record
)


def test_detect_duplicates():
    """Test duplicate detection logic."""
    records = [
        {"fighter_id": "7492", "opponent_name": "Islam", "event_name": "UFC 322"},
        {"fighter_id": "7492", "opponent_name": "Islam", "event_name": "UFC 322"},
    ]
    dupes = detect_duplicates(records)
    assert len(dupes) == 1  # One duplicate pair


def test_normalize_odds_format():
    """Test odds format normalization."""
    # Old format: mean_odds_values
    old_format = {
        "mean_odds_values": [{"time": 123, "odds": 2.5}]
    }
    normalized = normalize_odds_format(old_format)
    assert "mean_odds_history" in normalized
    assert normalized["mean_odds_history"][0]["timestamp_ms"] == 123

    # New format: pass through
    new_format = {
        "mean_odds_history": [{"timestamp_ms": 456, "odds": 3.0}]
    }
    normalized = normalize_odds_format(new_format)
    assert normalized["mean_odds_history"][0]["timestamp_ms"] == 456


def test_calculate_quality_tier():
    """Test quality tier assignment."""
    assert calculate_quality_tier(100) == "excellent"  # >50 points
    assert calculate_quality_tier(30) == "usable"  # >10 points
    assert calculate_quality_tier(3) == "poor"  # <=5 points
    assert calculate_quality_tier(0) == "no_data"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_clean_bfo_odds.py -v`
Expected: FAIL with "ModuleNotFoundError" or function not defined

**Step 3: Implement cleaning script**

```python
# scripts/clean_bfo_fighter_mean_odds.py
#!/usr/bin/env python3
"""
Clean and validate BFO fighter mean odds data.

This script:
1. Removes 216 duplicate records (keeps best quality)
2. Normalizes 78 old-format records
3. Assigns quality tiers based on data points
4. Validates data structure
5. Outputs clean dataset ready for database loading

Usage:
    python scripts/clean_bfo_fighter_mean_odds.py \
        --input data/raw/bfo_fighter_mean_odds.jsonl \
        --output data/processed/bfo_fighter_mean_odds_clean.jsonl
"""

import argparse
import json
import hashlib
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def generate_fight_key(record: dict[str, Any]) -> str:
    """Generate unique key for a fight record."""
    fighter_id = record.get("fighter_id", "")
    opponent = record.get("opponent_name", "").lower().strip()
    event = record.get("event_name", "").lower().strip()
    return f"{fighter_id}|{opponent}|{event}"


def detect_duplicates(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """
    Detect duplicate records by fighter+opponent+event.

    Returns:
        Dict mapping fight_key to list of duplicate records
    """
    fight_groups = defaultdict(list)

    for record in records:
        key = generate_fight_key(record)
        fight_groups[key].append(record)

    # Return only groups with duplicates
    duplicates = {k: v for k, v in fight_groups.items() if len(v) > 1}
    return duplicates


def select_best_duplicate(records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Select the best record from duplicates based on quality.

    Priority:
    1. Most data points in mean_odds_history
    2. Most recent scraped_at timestamp
    """
    if not records:
        return None

    if len(records) == 1:
        return records[0]

    # Sort by number of odds points (desc), then by scraped_at (desc)
    def sort_key(r):
        num_points = r.get("num_odds_points", 0)
        # Handle both formats
        if num_points == 0 and "mean_odds_history" in r:
            num_points = len(r["mean_odds_history"])

        scraped_at = r.get("scraped_at", "")
        return (-num_points, scraped_at)  # Negative for descending

    sorted_records = sorted(records, key=sort_key)
    return sorted_records[0]


def normalize_odds_format(record: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize old format (mean_odds_values) to new format (mean_odds_history).

    Old format: {"time": timestamp_ms, "odds": float}
    New format: {"timestamp_ms": int, "timestamp": ISO, "odds": float}
    """
    # Check if already in new format
    if "mean_odds_history" in record:
        return record

    # Convert old format
    if "mean_odds_values" in record:
        old_values = record.pop("mean_odds_values")
        new_history = []

        for point in old_values:
            ts_ms = point.get("time")
            odds = point.get("odds")

            if ts_ms and odds:
                new_history.append({
                    "timestamp_ms": ts_ms,
                    "timestamp": datetime.fromtimestamp(ts_ms / 1000).isoformat() + "Z",
                    "odds": odds
                })

        record["mean_odds_history"] = new_history
        record["num_odds_points"] = len(new_history)

    return record


def calculate_quality_tier(num_points: int) -> str:
    """
    Assign quality tier based on number of odds data points.

    Tiers:
    - excellent: >50 points (45.0% of data)
    - good: 30-50 points
    - usable: 10-30 points
    - poor: 1-10 points (7.4% of data)
    - no_data: 0 points (0.1% of data)
    """
    if num_points > 50:
        return "excellent"
    elif num_points >= 30:
        return "good"
    elif num_points >= 10:
        return "usable"
    elif num_points > 0:
        return "poor"
    else:
        return "no_data"


def validate_odds_record(record: dict[str, Any]) -> tuple[bool, str | None]:
    """
    Validate odds record structure and data.

    Returns:
        (is_valid, error_message)
    """
    required_fields = ["fighter_id", "opponent_name", "event_name"]

    for field in required_fields:
        if field not in record or not record[field]:
            return False, f"Missing required field: {field}"

    # Validate mean_odds_history structure
    if "mean_odds_history" not in record:
        return False, "Missing mean_odds_history field"

    history = record["mean_odds_history"]
    if not isinstance(history, list):
        return False, "mean_odds_history must be a list"

    # Validate data points have required fields
    for i, point in enumerate(history):
        if not isinstance(point, dict):
            return False, f"Data point {i} is not a dict"

        if "timestamp_ms" not in point or "odds" not in point:
            return False, f"Data point {i} missing timestamp_ms or odds"

    return True, None


def clean_odds_record(record: dict[str, Any]) -> dict[str, Any]:
    """
    Clean and enrich a single odds record.

    Steps:
    1. Normalize format
    2. Calculate quality tier
    3. Validate structure
    4. Add metadata
    """
    # Normalize format
    record = normalize_odds_format(record)

    # Calculate quality tier
    num_points = record.get("num_odds_points", len(record.get("mean_odds_history", [])))
    record["data_quality_tier"] = calculate_quality_tier(num_points)

    # Ensure num_odds_points is set
    if "num_odds_points" not in record or record["num_odds_points"] == 0:
        record["num_odds_points"] = len(record.get("mean_odds_history", []))

    # Clean string fields
    for field in ["fighter_name", "opponent_name", "event_name"]:
        if field in record and record[field]:
            record[field] = record[field].strip()

    return record


def main():
    parser = argparse.ArgumentParser(description="Clean BFO fighter odds data")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/bfo_fighter_mean_odds.jsonl"),
        help="Input JSONL file with raw scraped data"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/bfo_fighter_mean_odds_clean.jsonl"),
        help="Output JSONL file with cleaned data"
    )
    parser.add_argument(
        "--stats-output",
        type=Path,
        default=Path("data/processed/bfo_odds_cleaning_stats.json"),
        help="Output file for cleaning statistics"
    )

    args = parser.parse_args()

    print(f"Loading raw data from {args.input}...")

    # Load all records
    records = []
    with args.input.open() as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"Loaded {len(records)} records")

    # Step 1: Detect duplicates
    print("\nStep 1: Detecting duplicates...")
    duplicates = detect_duplicates(records)
    print(f"Found {len(duplicates)} duplicate fight groups")
    print(f"Total duplicate records: {sum(len(v) - 1 for v in duplicates.values())}")

    # Step 2: Remove duplicates (keep best)
    print("\nStep 2: Removing duplicates...")
    unique_records = []
    seen_keys = set()
    duplicates_removed = 0

    for record in records:
        key = generate_fight_key(record)

        if key in seen_keys:
            duplicates_removed += 1
            continue

        # If this is a duplicate group, select best
        if key in duplicates:
            best_record = select_best_duplicate(duplicates[key])
            unique_records.append(best_record)
            seen_keys.add(key)
        else:
            unique_records.append(record)
            seen_keys.add(key)

    print(f"Removed {duplicates_removed} duplicate records")
    print(f"Remaining: {len(unique_records)} unique records")

    # Step 3: Normalize format
    print("\nStep 3: Normalizing format...")
    old_format_count = 0
    normalized_records = []

    for record in unique_records:
        if "mean_odds_values" in record:
            old_format_count += 1
        normalized = clean_odds_record(record)
        normalized_records.append(normalized)

    print(f"Normalized {old_format_count} old-format records")

    # Step 4: Validate all records
    print("\nStep 4: Validating records...")
    valid_records = []
    invalid_records = []

    for record in normalized_records:
        is_valid, error = validate_odds_record(record)
        if is_valid:
            valid_records.append(record)
        else:
            invalid_records.append({"record": record, "error": error})

    print(f"Valid records: {len(valid_records)}")
    print(f"Invalid records: {len(invalid_records)}")

    if invalid_records:
        print("\nSample invalid records:")
        for item in invalid_records[:3]:
            print(f"  - {item['error']}")

    # Step 5: Calculate quality distribution
    print("\nStep 5: Quality distribution...")
    quality_counts = defaultdict(int)
    for record in valid_records:
        tier = record.get("data_quality_tier", "unknown")
        quality_counts[tier] += 1

    for tier, count in sorted(quality_counts.items()):
        pct = count / len(valid_records) * 100
        print(f"  {tier:12s}: {count:5d} ({pct:5.1f}%)")

    # Step 6: Write clean data
    print(f"\nWriting clean data to {args.output}...")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w") as f:
        for record in valid_records:
            f.write(json.dumps(record) + "\n")

    print(f"Wrote {len(valid_records)} clean records")

    # Step 7: Write cleaning stats
    stats = {
        "input_file": str(args.input),
        "output_file": str(args.output),
        "cleaned_at": datetime.utcnow().isoformat(),
        "input_records": len(records),
        "duplicates_removed": duplicates_removed,
        "old_format_normalized": old_format_count,
        "invalid_records": len(invalid_records),
        "output_records": len(valid_records),
        "quality_distribution": dict(quality_counts),
    }

    with args.stats_output.open("w") as f:
        json.dump(stats, f, indent=2)

    print(f"\nStats written to {args.stats_output}")
    print("\n✓ Data cleaning complete!")


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_clean_bfo_odds.py -v`
Expected: PASS

**Step 5: Run cleaning script**

```bash
python scripts/clean_bfo_fighter_mean_odds.py \
    --input data/raw/bfo_fighter_mean_odds.jsonl \
    --output data/processed/bfo_fighter_mean_odds_clean.jsonl
```

Expected output:
- Removes 216 duplicates
- Normalizes 78 old-format records
- Outputs ~13,838 clean records

**Step 6: Verify clean data**

```bash
wc -l data/processed/bfo_fighter_mean_odds_clean.jsonl
cat data/processed/bfo_odds_cleaning_stats.json | jq .
```

Expected: ~13,838 lines, stats show quality distribution

**Step 7: Commit**

```bash
git add scripts/clean_bfo_fighter_mean_odds.py tests/test_clean_bfo_odds.py
git add data/processed/bfo_fighter_mean_odds_clean.jsonl data/processed/bfo_odds_cleaning_stats.json
git commit -m "feat: data cleaning pipeline for BFO odds data

- Remove 216 duplicate records (keep best quality)
- Normalize 78 old-format records to new schema
- Assign quality tiers based on data point count
- Validate all records before output
- Output 13,838 clean records ready for DB load"
```

---

## Phase 3: Database Loading

### Task 4: Create Data Loading Script

**Files:**
- Create: `scripts/load_bfo_fighter_odds.py`
- Create: `tests/test_load_bfo_odds.py`

**Step 1: Write failing test**

```python
# tests/test_load_bfo_odds.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from scripts.load_bfo_fighter_odds import (
    generate_odds_id,
    parse_odds_record,
    load_odds_batch
)


def test_generate_odds_id():
    """Test odds ID generation from fighter+opponent+event."""
    record = {
        "fighter_id": "7492",
        "opponent_name": "Islam Makhachev",
        "event_name": "UFC 322"
    }
    odds_id = generate_odds_id(record)
    assert odds_id.startswith("odds_")
    assert len(odds_id) == 37  # "odds_" + 32 char hash


def test_parse_odds_record():
    """Test parsing cleaned JSONL record into DB format."""
    record = {
        "fighter_id": "7492",
        "fighter_name": "Jack Della Maddalena",
        "opponent_name": "Islam Makhachev",
        "event_name": "UFC 322",
        "opening_odds": "+275",
        "mean_odds_history": [
            {"timestamp_ms": 123, "timestamp": "2025-01-01T00:00:00Z", "odds": 3.75}
        ],
        "num_odds_points": 1,
        "data_quality_tier": "excellent"
    }

    parsed = parse_odds_record(record)
    assert parsed["id"].startswith("odds_")
    assert parsed["fighter_id"] == "7492"
    assert parsed["num_odds_points"] == 1
    assert len(parsed["mean_odds_history"]) == 1


@pytest.mark.asyncio
async def test_load_odds_batch():
    """Test batch loading of odds records."""
    mock_repo = AsyncMock()
    mock_repo.bulk_insert_odds = AsyncMock(return_value=5)

    records = [{"fighter_id": "123", "opponent_name": "Test"}] * 5

    inserted = await load_odds_batch(records, mock_repo)
    assert inserted == 5
    mock_repo.bulk_insert_odds.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_load_bfo_odds.py -v`
Expected: FAIL with module or function not found

**Step 3: Implement loading script**

```python
# scripts/load_bfo_fighter_odds.py
#!/usr/bin/env python3
"""
Load cleaned BFO fighter odds data into database.

This script:
1. Reads cleaned JSONL data
2. Converts to database format
3. Bulk inserts in batches
4. Handles conflicts (skip duplicates)
5. Reports progress and statistics

Usage:
    python scripts/load_bfo_fighter_odds.py \
        --input data/processed/bfo_fighter_mean_odds_clean.jsonl
"""

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.base import get_db_session
from backend.db.models import FighterOdds
from backend.db.repositories.odds import OddsRepository


def generate_odds_id(record: dict[str, Any]) -> str:
    """
    Generate deterministic ID for odds record.

    Format: odds_{hash(fighter_id + opponent + event)}
    """
    key = f"{record['fighter_id']}|{record['opponent_name']}|{record['event_name']}"
    hash_digest = hashlib.md5(key.encode()).hexdigest()
    return f"odds_{hash_digest}"


def parse_odds_record(record: dict[str, Any]) -> dict[str, Any]:
    """
    Parse cleaned JSONL record into database format.

    Returns:
        Dict suitable for FighterOdds model
    """
    odds_id = generate_odds_id(record)

    # Parse scraped_at timestamp
    scraped_at = record.get("scraped_at")
    if isinstance(scraped_at, str):
        try:
            scraped_at = datetime.fromisoformat(scraped_at.replace("Z", "+00:00"))
        except:
            scraped_at = datetime.utcnow()

    return {
        "id": odds_id,
        "fighter_id": record["fighter_id"],
        "opponent_name": record["opponent_name"],
        "event_name": record["event_name"],
        "event_url": record.get("event_url"),
        "event_date": None,  # TODO: Extract from event_name or lookup
        "opening_odds": record.get("opening_odds"),
        "closing_range_start": record.get("closing_range_start"),
        "closing_range_end": record.get("closing_range_end"),
        "mean_odds_history": record.get("mean_odds_history", []),
        "num_odds_points": record.get("num_odds_points", 0),
        "data_quality_tier": record.get("data_quality_tier"),
        "is_duplicate": False,
        "scraped_at": scraped_at,
        "bfo_fighter_url": record.get("fighter_url"),
    }


async def load_odds_batch(
    records: list[dict[str, Any]],
    repo: OddsRepository
) -> int:
    """
    Load batch of odds records into database.

    Returns:
        Number of records inserted
    """
    parsed_records = [parse_odds_record(r) for r in records]
    return await repo.bulk_insert_odds(parsed_records)


async def main_async(args):
    """Main async function."""
    print(f"Loading cleaned data from {args.input}...")

    # Load records
    records = []
    with args.input.open() as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"Loaded {len(records)} records")

    # Calculate batches
    batch_size = args.batch_size
    num_batches = (len(records) + batch_size - 1) // batch_size
    print(f"Processing in {num_batches} batches of {batch_size}")

    # Get database session
    async for session in get_db_session():
        repo = OddsRepository(session)

        total_inserted = 0
        total_skipped = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            batch_num = i // batch_size + 1

            print(f"\nBatch {batch_num}/{num_batches} ({len(batch)} records)...")

            try:
                inserted = await load_odds_batch(batch, repo)
                total_inserted += inserted
                skipped = len(batch) - inserted
                total_skipped += skipped

                print(f"  Inserted: {inserted}")
                if skipped > 0:
                    print(f"  Skipped (duplicates): {skipped}")

            except Exception as e:
                print(f"  Error: {e}")
                if not args.continue_on_error:
                    raise

        # Final summary
        print(f"\n{'=' * 60}")
        print(f"Loading complete!")
        print(f"{'=' * 60}")
        print(f"Total records processed: {len(records)}")
        print(f"Total inserted: {total_inserted}")
        print(f"Total skipped: {total_skipped}")
        print(f"Success rate: {total_inserted / len(records) * 100:.1f}%")


def main():
    parser = argparse.ArgumentParser(description="Load BFO fighter odds into database")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/bfo_fighter_mean_odds_clean.jsonl"),
        help="Input JSONL file with cleaned data"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of records per batch (default: 100)"
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue processing if a batch fails"
    )

    args = parser.parse_args()

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
```

**Step 4: Create OddsRepository**

```python
# backend/db/repositories/odds.py
from __future__ import annotations

from typing import Any

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import FighterOdds


class OddsRepository:
    """Repository for fighter odds data operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_insert_odds(self, records: list[dict[str, Any]]) -> int:
        """
        Bulk insert odds records, skipping duplicates.

        Returns:
            Number of records inserted
        """
        if not records:
            return 0

        # Use PostgreSQL INSERT ... ON CONFLICT DO NOTHING
        stmt = insert(FighterOdds).values(records)
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_fighter_odds_fight"
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount

    async def get_fighter_odds_history(
        self,
        fighter_id: str,
        limit: int = 100
    ) -> list[FighterOdds]:
        """Get odds history for a fighter."""
        stmt = (
            select(FighterOdds)
            .where(FighterOdds.fighter_id == fighter_id)
            .order_by(FighterOdds.event_date.desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_fighter_odds_count(self, fighter_id: str) -> int:
        """Get count of odds records for a fighter."""
        stmt = (
            select(func.count(FighterOdds.id))
            .where(FighterOdds.fighter_id == fighter_id)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one()
```

**Step 5: Run tests**

Run: `pytest tests/test_load_bfo_odds.py -v`
Expected: PASS

**Step 6: Run loading script**

```bash
python scripts/load_bfo_fighter_odds.py \
    --input data/processed/bfo_fighter_mean_odds_clean.jsonl \
    --batch-size 100
```

Expected: ~13,838 records inserted successfully

**Step 7: Verify data in database**

```bash
PGPASSWORD=ufc_pokedex psql -h localhost -p 5432 -U ufc_pokedex -d ufc_pokedex -c "
SELECT
    COUNT(*) as total_records,
    COUNT(DISTINCT fighter_id) as unique_fighters,
    AVG(num_odds_points) as avg_points,
    data_quality_tier,
    COUNT(*) as tier_count
FROM fighter_odds
GROUP BY data_quality_tier
ORDER BY tier_count DESC;
"
```

Expected: ~13,838 records, ~1,255 fighters, quality distribution matches

**Step 8: Commit**

```bash
git add scripts/load_bfo_fighter_odds.py backend/db/repositories/odds.py tests/test_load_bfo_odds.py
git commit -m "feat: database loading pipeline for BFO odds data

- Bulk insert in batches with conflict handling
- Skip duplicate records using unique constraint
- OddsRepository with bulk insert and query methods
- Progress tracking and error handling"
```

---

## Phase 4: API Endpoints

### Task 5: Create Odds API Endpoints

**Files:**
- Create: `backend/api/odds.py`
- Modify: `backend/api/__init__.py` (register routes)
- Create: `tests/test_api_odds.py`

**Step 1: Write failing test**

```python
# tests/test_api_odds.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app


client = TestClient(app)


def test_get_fighter_odds_history():
    """Test GET /api/odds/fighter/{fighter_id}"""
    response = client.get("/api/odds/fighter/7492")
    assert response.status_code == 200

    data = response.json()
    assert "odds_history" in data
    assert "total_fights" in data
    assert isinstance(data["odds_history"], list)


def test_get_fighter_odds_chart():
    """Test GET /api/odds/fighter/{fighter_id}/chart"""
    response = client.get("/api/odds/fighter/7492/chart")
    assert response.status_code == 200

    data = response.json()
    assert "fights" in data
    assert isinstance(data["fights"], list)


def test_get_odds_quality_stats():
    """Test GET /api/odds/stats/quality"""
    response = client.get("/api/odds/stats/quality")
    assert response.status_code == 200

    data = response.json()
    assert "total_records" in data
    assert "quality_distribution" in data
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_api_odds.py -v`
Expected: FAIL with 404 or endpoint not found

**Step 3: Implement API endpoints**

```python
# backend/api/odds.py
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import get_db_session
from backend.db.repositories.odds import OddsRepository

router = APIRouter(prefix="/odds", tags=["odds"])


@router.get("/fighter/{fighter_id}")
async def get_fighter_odds_history(
    fighter_id: str,
    limit: int = 100,
    session: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """
    Get betting odds history for a fighter.

    Returns list of fights with odds data, sorted by date descending.
    """
    repo = OddsRepository(session)

    odds_records = await repo.get_fighter_odds_history(fighter_id, limit=limit)
    total_count = await repo.get_fighter_odds_count(fighter_id)

    return {
        "fighter_id": fighter_id,
        "total_fights": total_count,
        "returned": len(odds_records),
        "odds_history": [
            {
                "id": record.id,
                "opponent_name": record.opponent_name,
                "event_name": record.event_name,
                "event_date": record.event_date.isoformat() if record.event_date else None,
                "opening_odds": record.opening_odds,
                "closing_range": {
                    "start": record.closing_range_start,
                    "end": record.closing_range_end
                },
                "num_odds_points": record.num_odds_points,
                "data_quality": record.data_quality_tier,
            }
            for record in odds_records
        ]
    }


@router.get("/fighter/{fighter_id}/chart")
async def get_fighter_odds_chart_data(
    fighter_id: str,
    limit: int = 20,
    session: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """
    Get odds time-series data for chart visualization.

    Returns formatted data for Recharts line charts.
    """
    repo = OddsRepository(session)

    odds_records = await repo.get_fighter_odds_history(fighter_id, limit=limit)

    if not odds_records:
        raise HTTPException(status_code=404, detail="No odds data found for fighter")

    # Format for charting
    fights = []
    for record in odds_records:
        fight_data = {
            "fight_id": record.id,
            "opponent": record.opponent_name,
            "event": record.event_name,
            "event_date": record.event_date.isoformat() if record.event_date else None,
            "opening_odds": record.opening_odds,
            "closing_odds": record.closing_range_end or record.closing_range_start,
            "time_series": record.mean_odds_history,
            "quality": record.data_quality_tier,
        }
        fights.append(fight_data)

    return {
        "fighter_id": fighter_id,
        "fights": fights
    }


@router.get("/fight/{odds_id}")
async def get_fight_odds_detail(
    odds_id: str,
    session: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """
    Get detailed odds data for a specific fight.

    Includes full time-series data.
    """
    repo = OddsRepository(session)

    record = await repo.get_odds_by_id(odds_id)

    if not record:
        raise HTTPException(status_code=404, detail="Odds record not found")

    return {
        "id": record.id,
        "fighter_id": record.fighter_id,
        "opponent_name": record.opponent_name,
        "event_name": record.event_name,
        "event_date": record.event_date.isoformat() if record.event_date else None,
        "event_url": record.event_url,
        "opening_odds": record.opening_odds,
        "closing_range": {
            "start": record.closing_range_start,
            "end": record.closing_range_end
        },
        "mean_odds_history": record.mean_odds_history,
        "num_odds_points": record.num_odds_points,
        "data_quality": record.data_quality_tier,
        "scraped_at": record.scraped_at.isoformat(),
    }


@router.get("/stats/quality")
async def get_odds_quality_stats(
    session: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """
    Get data quality statistics for odds dataset.
    """
    repo = OddsRepository(session)

    stats = await repo.get_quality_stats()

    return {
        "total_records": stats["total"],
        "unique_fighters": stats["unique_fighters"],
        "quality_distribution": stats["quality_distribution"],
        "avg_odds_points": stats["avg_points"],
    }
```

**Step 4: Add repository methods**

```python
# backend/db/repositories/odds.py (add to existing file)

async def get_odds_by_id(self, odds_id: str) -> FighterOdds | None:
    """Get odds record by ID."""
    stmt = select(FighterOdds).where(FighterOdds.id == odds_id)
    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()

async def get_quality_stats(self) -> dict[str, Any]:
    """Get quality statistics for odds dataset."""
    # Total count
    total_stmt = select(func.count(FighterOdds.id))
    total_result = await self.session.execute(total_stmt)
    total = total_result.scalar_one()

    # Unique fighters
    fighters_stmt = select(func.count(func.distinct(FighterOdds.fighter_id)))
    fighters_result = await self.session.execute(fighters_stmt)
    unique_fighters = fighters_result.scalar_one()

    # Quality distribution
    quality_stmt = (
        select(
            FighterOdds.data_quality_tier,
            func.count(FighterOdds.id).label("count")
        )
        .group_by(FighterOdds.data_quality_tier)
    )
    quality_result = await self.session.execute(quality_stmt)
    quality_distribution = {row.data_quality_tier: row.count for row in quality_result}

    # Average points
    avg_stmt = select(func.avg(FighterOdds.num_odds_points))
    avg_result = await self.session.execute(avg_stmt)
    avg_points = float(avg_result.scalar_one() or 0)

    return {
        "total": total,
        "unique_fighters": unique_fighters,
        "quality_distribution": quality_distribution,
        "avg_points": avg_points,
    }
```

**Step 5: Register routes**

```python
# backend/api/__init__.py (add import)
from .odds import router as odds_router

# In create_app():
app.include_router(odds_router, prefix="/api")
```

**Step 6: Run tests**

Run: `pytest tests/test_api_odds.py -v`
Expected: PASS

**Step 7: Manual API testing**

```bash
# Start dev server
make dev

# Test endpoints
curl http://localhost:8000/api/odds/fighter/7492 | jq .
curl http://localhost:8000/api/odds/stats/quality | jq .
```

Expected: JSON responses with odds data

**Step 8: Commit**

```bash
git add backend/api/odds.py backend/api/__init__.py backend/db/repositories/odds.py tests/test_api_odds.py
git commit -m "feat: REST API endpoints for fighter odds data

- GET /api/odds/fighter/{id} - fighter odds history
- GET /api/odds/fighter/{id}/chart - chart-ready data
- GET /api/odds/fight/{id} - detailed fight odds
- GET /api/odds/stats/quality - quality statistics
- Repository methods for stats and queries"
```

---

## Phase 5: Frontend Integration

### Task 6: Create Odds Chart Component

**Files:**
- Create: `frontend/src/components/FighterOddsChart.tsx`
- Create: `frontend/src/app/fighters/[id]/odds/page.tsx`
- Create: `frontend/src/hooks/useOddsData.ts`

**Step 1: Create TypeScript types**

```typescript
// frontend/src/types/odds.ts
export interface OddsDataPoint {
  timestamp_ms: number;
  timestamp: string;
  odds: number;
}

export interface FightOdds {
  fight_id: string;
  opponent: string;
  event: string;
  event_date: string | null;
  opening_odds: string | null;
  closing_odds: string | null;
  time_series: OddsDataPoint[];
  quality: 'excellent' | 'good' | 'usable' | 'poor' | 'no_data';
}

export interface OddsChartData {
  fighter_id: string;
  fights: FightOdds[];
}

export interface OddsHistoryItem {
  id: string;
  opponent_name: string;
  event_name: string;
  event_date: string | null;
  opening_odds: string | null;
  closing_range: {
    start: string | null;
    end: string | null;
  };
  num_odds_points: number;
  data_quality: string;
}

export interface OddsHistory {
  fighter_id: string;
  total_fights: number;
  returned: number;
  odds_history: OddsHistoryItem[];
}
```

**Step 2: Create data fetching hook**

```typescript
// frontend/src/hooks/useOddsData.ts
import { useQuery } from '@tanstack/react-query';
import { OddsChartData, OddsHistory } from '@/types/odds';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function useOddsChart(fighterId: string | undefined) {
  return useQuery<OddsChartData>({
    queryKey: ['odds', 'chart', fighterId],
    queryFn: async () => {
      if (!fighterId) throw new Error('Fighter ID required');

      const response = await fetch(
        `${API_URL}/api/odds/fighter/${fighterId}/chart`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch odds data');
      }

      return response.json();
    },
    enabled: !!fighterId,
  });
}

export function useOddsHistory(fighterId: string | undefined) {
  return useQuery<OddsHistory>({
    queryKey: ['odds', 'history', fighterId],
    queryFn: async () => {
      if (!fighterId) throw new Error('Fighter ID required');

      const response = await fetch(
        `${API_URL}/api/odds/fighter/${fighterId}`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch odds history');
      }

      return response.json();
    },
    enabled: !!fighterId,
  });
}
```

**Step 3: Create chart component**

```typescript
// frontend/src/components/FighterOddsChart.tsx
'use client';

import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { FightOdds, OddsDataPoint } from '@/types/odds';

interface FighterOddsChartProps {
  fights: FightOdds[];
  selectedFightId?: string;
}

export function FighterOddsChart({ fights, selectedFightId }: FighterOddsChartProps) {
  const selectedFight = useMemo(
    () => fights.find((f) => f.fight_id === selectedFightId) || fights[0],
    [fights, selectedFightId]
  );

  const chartData = useMemo(() => {
    if (!selectedFight) return [];

    return selectedFight.time_series.map((point: OddsDataPoint) => ({
      timestamp: new Date(point.timestamp_ms).toLocaleDateString(),
      odds: point.odds,
      date: new Date(point.timestamp_ms),
    }));
  }, [selectedFight]);

  if (!selectedFight || chartData.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No odds data available for this fight
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">
            vs {selectedFight.opponent}
          </h3>
          <p className="text-sm text-muted-foreground">
            {selectedFight.event}
            {selectedFight.event_date && ` • ${new Date(selectedFight.event_date).toLocaleDateString()}`}
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm">
            Opening: <span className="font-mono">{selectedFight.opening_odds || 'N/A'}</span>
          </p>
          <p className="text-sm">
            Closing: <span className="font-mono">{selectedFight.closing_odds || 'N/A'}</span>
          </p>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey="timestamp"
            className="text-sm"
            tick={{ fill: 'currentColor' }}
          />
          <YAxis
            label={{ value: 'Odds (Decimal)', angle: -90, position: 'insideLeft' }}
            domain={['auto', 'auto']}
            className="text-sm"
            tick={{ fill: 'currentColor' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--background))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
            }}
            labelStyle={{ color: 'hsl(var(--foreground))' }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="odds"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
            name="Mean Odds"
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span className="inline-block w-2 h-2 rounded-full bg-primary" />
        <span>{chartData.length} data points</span>
        <span>•</span>
        <span className="capitalize">Quality: {selectedFight.quality}</span>
      </div>
    </div>
  );
}
```

**Step 4: Create odds page**

```typescript
// frontend/src/app/fighters/[id]/odds/page.tsx
'use client';

import { useParams } from 'next/navigation';
import { useState } from 'react';
import { FighterOddsChart } from '@/components/FighterOddsChart';
import { useOddsChart, useOddsHistory } from '@/hooks/useOddsData';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export default function FighterOddsPage() {
  const params = useParams();
  const fighterId = params?.id as string;

  const [selectedFightId, setSelectedFightId] = useState<string>();

  const { data: chartData, isLoading: chartLoading } = useOddsChart(fighterId);
  const { data: historyData, isLoading: historyLoading } = useOddsHistory(fighterId);

  if (chartLoading || historyLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-[400px] w-full" />
        <Skeleton className="h-[200px] w-full" />
      </div>
    );
  }

  if (!chartData || !chartData.fights || chartData.fights.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No betting odds data available for this fighter
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Betting Odds History</CardTitle>
        </CardHeader>
        <CardContent>
          <FighterOddsChart
            fights={chartData.fights}
            selectedFightId={selectedFightId}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>All Fights ({historyData?.total_fights || 0})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {historyData?.odds_history.map((fight) => (
              <button
                key={fight.id}
                onClick={() => setSelectedFightId(fight.id)}
                className={`w-full text-left p-3 rounded-lg border transition-colors ${
                  selectedFightId === fight.id
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:bg-muted'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{fight.opponent_name}</p>
                    <p className="text-sm text-muted-foreground">{fight.event_name}</p>
                  </div>
                  <div className="text-right text-sm">
                    <p className="font-mono">{fight.opening_odds || 'N/A'}</p>
                    <p className="text-muted-foreground">
                      {fight.num_odds_points} pts
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Step 5: Add navigation link**

```typescript
// frontend/src/app/fighters/[id]/layout.tsx (add tab)
<Link href={`/fighters/${params.id}/odds`}>
  Betting Odds
</Link>
```

**Step 6: Test frontend**

```bash
cd frontend
pnpm dev

# Visit http://localhost:3000/fighters/7492/odds
```

Expected: Chart displays odds history with interactive fight selection

**Step 7: Commit**

```bash
git add frontend/src/components/FighterOddsChart.tsx frontend/src/app/fighters/[id]/odds/page.tsx frontend/src/hooks/useOddsData.ts frontend/src/types/odds.ts
git commit -m "feat: fighter odds visualization with interactive charts

- LineChart component showing odds movement over time
- Fight selector for viewing different matchups
- Quality indicators and data point counts
- Responsive design with proper loading states
- Integration with /api/odds endpoints"
```

---

## Phase 6: Documentation & Testing

### Task 7: Add API Documentation

**Files:**
- Modify: `backend/api/odds.py` (add OpenAPI docs)
- Create: `docs/api/odds-endpoints.md`

**Step 1: Enhance OpenAPI documentation**

Add detailed docstrings to all endpoints in `backend/api/odds.py` with:
- Parameter descriptions
- Response schemas
- Example responses
- Error codes

**Step 2: Create API documentation**

```markdown
# docs/api/odds-endpoints.md

# Fighter Odds API Endpoints

## Overview

The Fighter Odds API provides access to betting odds history from BestFightOdds.com for UFC fighters.

## Endpoints

### GET /api/odds/fighter/{fighter_id}

Get betting odds history for a specific fighter.

**Parameters:**
- `fighter_id` (path, required): Fighter ID from UFC Stats
- `limit` (query, optional): Max records to return (default: 100)

**Response:**
```json
{
  "fighter_id": "7492",
  "total_fights": 25,
  "returned": 25,
  "odds_history": [...]
}
```

### GET /api/odds/fighter/{fighter_id}/chart

Get chart-ready odds data for visualization.

... (continue with full documentation)
```

**Step 3: Test API documentation**

Visit `http://localhost:8000/docs` and verify all odds endpoints are documented

**Step 4: Commit**

```bash
git add backend/api/odds.py docs/api/odds-endpoints.md
git commit -m "docs: comprehensive API documentation for odds endpoints

- Enhanced OpenAPI docstrings
- Example requests and responses
- Error handling documentation
- Usage examples"
```

---

### Task 8: Integration Tests

**Files:**
- Create: `tests/integration/test_odds_pipeline.py`

**Step 1: Write integration test**

```python
# tests/integration/test_odds_pipeline.py
"""
End-to-end integration tests for odds pipeline.

Tests the complete flow:
1. Clean raw data
2. Load into database
3. Query via repository
4. Fetch via API
"""

import pytest
from pathlib import Path
import json


@pytest.mark.integration
async def test_complete_odds_pipeline(test_db, test_client):
    """Test complete pipeline from raw data to API response."""

    # 1. Clean test data
    # (Assuming clean_bfo_fighter_mean_odds can be imported)
    from scripts.clean_bfo_fighter_mean_odds import clean_odds_record

    raw_record = {
        "fighter_id": "test123",
        "opponent_name": "Test Opponent",
        "event_name": "Test Event",
        "mean_odds_history": [
            {"timestamp_ms": 123, "timestamp": "2025-01-01T00:00:00Z", "odds": 2.5}
        ]
    }

    cleaned = clean_odds_record(raw_record)
    assert cleaned["data_quality_tier"] in ["excellent", "good", "usable", "poor", "no_data"]

    # 2. Load into test database
    from backend.db.repositories.odds import OddsRepository
    repo = OddsRepository(test_db)

    from scripts.load_bfo_fighter_odds import parse_odds_record
    db_record = parse_odds_record(cleaned)

    inserted = await repo.bulk_insert_odds([db_record])
    assert inserted == 1

    # 3. Query via repository
    odds_list = await repo.get_fighter_odds_history("test123")
    assert len(odds_list) == 1
    assert odds_list[0].opponent_name == "Test Opponent"

    # 4. Fetch via API
    response = test_client.get("/api/odds/fighter/test123")
    assert response.status_code == 200

    data = response.json()
    assert data["total_fights"] == 1
    assert data["odds_history"][0]["opponent_name"] == "Test Opponent"
```

**Step 2: Run integration tests**

Run: `pytest tests/integration/test_odds_pipeline.py -v -m integration`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_odds_pipeline.py
git commit -m "test: end-to-end integration tests for odds pipeline

- Test complete flow from raw data to API
- Validate data cleaning, loading, and querying
- Integration test markers for CI/CD"
```

---

## Phase 7: Production Deployment

### Task 9: Run Production Data Load

**Files:**
- Create: `scripts/production_odds_load.sh`

**Step 1: Create production load script**

```bash
# scripts/production_odds_load.sh
#!/bin/bash
set -euo pipefail

echo "=================================================="
echo "BFO Fighter Odds - Production Data Load"
echo "=================================================="

# Step 1: Backup current database
echo -e "\n[1/5] Creating database backup..."
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -Fc -f "backups/pre_odds_load_$(date +%Y%m%d_%H%M%S).dump"

# Step 2: Clean data
echo -e "\n[2/5] Cleaning raw data..."
python scripts/clean_bfo_fighter_mean_odds.py \
    --input data/raw/bfo_fighter_mean_odds.jsonl \
    --output data/processed/bfo_fighter_mean_odds_clean.jsonl

# Step 3: Validate clean data
echo -e "\n[3/5] Validating clean data..."
CLEAN_COUNT=$(wc -l < data/processed/bfo_fighter_mean_odds_clean.jsonl)
echo "Clean records: $CLEAN_COUNT"

if [ "$CLEAN_COUNT" -lt 13000 ]; then
    echo "ERROR: Clean data count too low (expected ~13,838)"
    exit 1
fi

# Step 4: Load into database
echo -e "\n[4/5] Loading data into database..."
python scripts/load_bfo_fighter_odds.py \
    --input data/processed/bfo_fighter_mean_odds_clean.jsonl \
    --batch-size 100

# Step 5: Verify data
echo -e "\n[5/5] Verifying data in database..."
LOADED_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM fighter_odds;")

echo "Records in database: $LOADED_COUNT"

if [ "$LOADED_COUNT" -lt 13000 ]; then
    echo "ERROR: Database count too low"
    exit 1
fi

echo -e "\n=================================================="
echo "✓ Production data load complete!"
echo "=================================================="
```

**Step 2: Run production load (dry run first)**

```bash
# Dry run on development database
DATABASE_URL="postgresql://..." bash scripts/production_odds_load.sh
```

**Step 3: Run on production**

```bash
# Production load with monitoring
DATABASE_URL="$PROD_DATABASE_URL" bash scripts/production_odds_load.sh 2>&1 | tee logs/prod_odds_load.log
```

**Step 4: Verify production data**

```bash
# Check via API
curl https://api.ufc.wolfgangschoenberger.com/api/odds/stats/quality | jq .

# Check in database
PGPASSWORD=$PROD_DB_PASSWORD psql -h $PROD_DB_HOST -U $PROD_DB_USER -d $PROD_DB_NAME -c "
SELECT COUNT(*) as total, data_quality_tier
FROM fighter_odds
GROUP BY data_quality_tier;
"
```

Expected: ~13,838 records, quality distribution matches

**Step 5: Commit**

```bash
git add scripts/production_odds_load.sh
git commit -m "deploy: production data load script for BFO odds

- Automated pipeline with backup and validation
- Error checking and rollback capability
- Production deployment checklist"
```

---

## Summary & Verification

### Final Verification Checklist

**Database:**
- [ ] `fighter_odds` table exists with all columns
- [ ] ~13,838 records loaded
- [ ] ~1,255 unique fighters covered
- [ ] Indexes created and used in queries
- [ ] Foreign key constraint to fighters table

**Data Quality:**
- [ ] 216 duplicates removed
- [ ] 78 old-format records normalized
- [ ] Quality tiers assigned correctly
- [ ] No validation errors

**API Endpoints:**
- [ ] GET /api/odds/fighter/{id} returns odds history
- [ ] GET /api/odds/fighter/{id}/chart returns chart data
- [ ] GET /api/odds/fight/{id} returns fight details
- [ ] GET /api/odds/stats/quality returns quality stats
- [ ] All endpoints documented in OpenAPI

**Frontend:**
- [ ] Odds chart displays time-series data
- [ ] Fight selector works interactively
- [ ] Quality indicators visible
- [ ] Loading states and errors handled

**Tests:**
- [ ] Unit tests pass for all components
- [ ] Integration tests pass end-to-end
- [ ] API tests cover all endpoints

**Production:**
- [ ] Production load script tested
- [ ] Data verified in production database
- [ ] API endpoints accessible publicly
- [ ] Frontend deployed and functional

---

## Next Steps After Plan Completion

1. **Event Date Enrichment**: Extract or lookup event dates for better timeline visualization
2. **Fight Result Integration**: Link odds records to fight results in `fights` table
3. **Odds Analytics**: Calculate ROI, favorite vs underdog statistics, closing line value
4. **Historical Scraper**: Set up scheduled scraper to update odds for upcoming events
5. **Performance Optimization**: Add materialized views for common aggregations
6. **Advanced Visualizations**: Multi-fight comparison charts, odds movement patterns

---

**Plan created:** 2025-11-13
**Target completion:** 2-3 days (8-12 hours of development)
**Estimated LOC:** ~1,500 lines (backend + frontend + tests)

11/13/2025 05:41 PM
