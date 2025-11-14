# BFO Fighter Odds Integration - Implementation Specification

**Project:** UFC Pokedex
**Feature:** Betting Odds Data Integration
**Author:** Engineering Team
**Created:** 2025-11-13
**Status:** Ready for Implementation
**Estimated Effort:** Backend MVP 16–24 hours; full odds feature (backend + frontend + monitoring) 32–40 hours
**Target:** Production deployment with full test coverage

---

## Executive Summary

Integrate 14,054 scraped betting odds records from BestFightOdds.com into the UFC Pokedex platform. The scrapers are **already complete and working**—this spec covers the missing database layer, API endpoints, and frontend visualization.

### What We Have
- ✅ 8 working BFO scrapers (event lists, fighter pages, line movement)
- ✅ 14,054 odds records scraped (`data/raw/bfo_fighter_mean_odds.jsonl`)
- ✅ 1,255/1,262 fighters covered (99.4% coverage)
- ✅ Bookmaker mapping infrastructure (Tier 1 filtering, major books)
- ✅ Comprehensive data quality analysis (≈88% of cleaned records have ≥10 time-series points)

### What We Need
- ❌ Database schema for storing odds
- ❌ Data cleaning pipeline (remove 216 duplicates, normalize 78 old-format records)
- ❌ Repository layer for odds queries
- ❌ API endpoints for odds data access
- ❌ Frontend components for odds visualization
- ❌ Integration tests

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Data Quality Analysis](#data-quality-analysis)
3. [Implementation Phases](#implementation-phases)
4. [Database Schema](#database-schema)
5. [Data Pipeline](#data-pipeline)
6. [API Design](#api-design)
7. [Frontend Components](#frontend-components)
8. [Testing Strategy](#testing-strategy)
9. [Deployment Plan](#deployment-plan)
10. [Success Criteria](#success-criteria)
11. [Risk Mitigation](#risk-mitigation)

---

## Architecture Overview

### System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                     BFO ODDS INTEGRATION                        │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  BestFightOdds   │  Already scraped, 14,054 records in JSONL
│   (External)     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Data Cleaning   │  NEW: Remove dupes, normalize formats
│    Pipeline      │       Assign quality tiers
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   PostgreSQL     │  NEW: fighter_odds table
│   Database       │       Time-series JSON storage
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  OddsRepository  │  NEW: Query layer with caching
│   + Service      │       Follows existing patterns
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   FastAPI        │  NEW: /api/odds endpoints
│   Endpoints      │       OpenAPI documentation
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Next.js + React │  NEW: OddsChart component
│    Frontend      │       Interactive visualizations
└──────────────────┘
```

### Design Principles

1. **Follow Existing Patterns**: Match the architecture used by fighters, rankings, and events modules
2. **Async-First**: All database operations use SQLAlchemy AsyncSession
3. **Type Safety**: Full type coverage in Python (Pydantic) and TypeScript
4. **Cacheable**: Service layer caching with Redis + in-memory fallback
5. **Testable**: Repository/Service/API tested independently
6. **Production-Ready**: Error handling, logging, monitoring hooks

### Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Database | PostgreSQL 12+ | Time-series JSON, advanced indexing |
| ORM | SQLAlchemy 2.0 + Alembic | Async, typed, migrations |
| Caching | Redis 6.0+ | With in-memory fallback |
| API | FastAPI | Async endpoints, auto OpenAPI docs |
| Frontend | Next.js 14 + TypeScript | Server components, RSC |
| Charts | Recharts | Line charts for odds movement |
| Testing | Pytest + Playwright | Unit, integration, E2E |

---

## Data Quality Analysis

### Dataset Overview

| Metric | Value | Notes |
|--------|-------|-------|
| Total records (raw) | 14,054 | From full scrape before cleaning |
| Total records (clean) | 13,838 | After deduplication and format normalization |
| Unique fighters | 1,255 / 1,262 | 99.4% coverage |
| Avg fights/fighter | 11.2 | Realistic distribution |
| Avg data points/fight | 78 | Sufficient for trends |
| Median data points | 45 | Good quality baseline |
| Max data points | 1,444 | Exceptional coverage |

### Quality Distribution

All percentages below are calculated over the **cleaned dataset** of 13,838 records.

| Tier | Threshold | Count | Percentage |
|------|-----------|-------|------------|
| Excellent | >50 points | 6,327 | 45.7% |
| Good | 30-50 points | 3,500 | 25.3% |
| Usable | 10-30 points | 2,400 | 17.3% |
| Poor | 1-10 points | 1,594 | 11.5% |
| No data | 0 points | 17 | 0.1% |

**High-quality coverage:** (excellent + good + usable) / cleaned total  
→ (6,327 + 3,500 + 2,400) / 13,838 ≈ **88%** of records have ≥10 data points.

### Data Issues

1. **Duplicates** (216 records, 1.5%)
   - Cause: Script ran multiple times before deduplication fix
   - Resolution: Keep best quality (most data points, most recent scrape)
   - Status: Script fix applied, won't recur

2. **Format Mix** (78 records, 0.6%)
   - Old format: `mean_odds_values` → `[{time, odds}]`
   - New format: `mean_odds_history` → `[{timestamp_ms, timestamp, odds}]`
   - Resolution: Normalize to new format during cleaning

3. **Missing Odds** (17 records, 0.1%)
   - Cause: Fights not tracked by bookmakers (regional, old fights)
   - Resolution: Flag with `data_quality_tier: "no_data"`
   - Action: Keep records for completeness, filter in queries

4. **Low Data Points** (1,611 records, 11.6%)
   - Cause: Old fights, regional promotions, limited bookmaker coverage
   - Resolution: Assign quality tier, allow filtering by quality
   - Action: Keep all records, expose quality metadata

---

## Implementation Phases

### Phase 1: Foundation (4-6 hours)

**Goal:** Database schema and migration

**Tasks:**
1. Create `FighterOdds` SQLAlchemy model
2. Write Alembic migration
3. Apply migration to dev database
4. Verify table creation and indexes

**Deliverables:**
- `backend/db/models/odds.py`
- `backend/db/migrations/versions/XXXX_add_fighter_odds.py`
- Unit tests for model validation

**Success Criteria:**
- Migration applies cleanly
- All indexes created
- Foreign key constraints validated
- Model instantiation tests pass

---

### Phase 2: Data Pipeline (4-6 hours)

**Goal:** Clean and load 13,838 records into database

**Tasks:**
1. Implement data cleaning script
   - Detect and remove duplicates
   - Normalize old format records
   - Calculate quality tiers
   - Validate structure
2. Implement data loading script
   - Bulk insert with conflict handling
   - Progress tracking
   - Error recovery
3. Run full pipeline on production dataset
4. Verify data quality in database

**Deliverables:**
- `scripts/clean_bfo_fighter_mean_odds.py`
- `scripts/load_bfo_fighter_odds.py`
- `backend/db/repositories/odds.py`
- `data/processed/bfo_fighter_mean_odds_clean.jsonl`
- Cleaning statistics report

**Success Criteria:**
- 13,838 clean records (14,054 - 216 duplicates)
- Zero validation errors
- All quality tiers assigned correctly
- Database contains expected record count
- Query performance meets SLA (<100ms for fighter odds history)

---

### Phase 3: Service & Repository Layer (3-4 hours)

**Goal:** Query layer with caching

**Tasks:**
1. Implement `OddsRepository` with core queries
   - `get_fighter_odds_history(fighter_id, limit)`
   - `get_fight_odds_detail(odds_id)`
   - `get_quality_stats()`
2. Implement `OddsQueryService` with business logic
   - Apply quality filtering
   - Cache common queries using `CacheableService` + `@cached` from `backend/services/caching.py`
   - Transform to response schemas
3. Write repository and service tests

**Deliverables:**
- `backend/db/repositories/odds.py`
- `backend/services/odds_query_service.py`
- `backend/services/dependencies.py` (register service)
- `tests/backend/test_odds_repository.py`
- `tests/backend/test_odds_service.py`

**Success Criteria:**
- All repository methods tested with real PostgreSQL
- Service caching verified (cache hit/miss)
- Query performance <100ms (99th percentile)
- Async patterns consistent with existing services

---

### Phase 4: API Endpoints (2-3 hours)

**Goal:** RESTful API for odds data

**Tasks:**
1. Implement API endpoints
   - `GET /api/odds/fighter/{id}` - Odds history
   - `GET /api/odds/fighter/{id}/chart` - Chart-ready data
   - `GET /api/odds/fight/{id}` - Fight detail
   - `GET /api/odds/stats/quality` - Quality statistics
2. Create Pydantic response schemas
3. Add OpenAPI documentation
4. Write API integration tests

**Deliverables:**
- `backend/api/odds.py`
- `backend/schemas/odds.py`
- `tests/backend/test_odds_api.py`
- OpenAPI documentation at `/docs`

**Success Criteria:**
- All endpoints return correct status codes
- Pagination working correctly
- Error handling (404, 500) properly implemented
- OpenAPI docs complete with examples
- Response times <200ms (99th percentile)

---

### Phase 5: Frontend Integration (3-4 hours)

**Goal:** Interactive odds visualization

**Tasks:**
1. Create TypeScript types for odds data
2. Implement data fetching hooks
   - `useOddsChart(fighterId)`
   - `useOddsHistory(fighterId)`
3. Create `FighterOddsChart` component
   - Recharts line chart
   - Interactive fight selector
   - Quality indicators
4. Create odds page `/fighters/[id]/odds`
5. Add navigation entry from the main fighter detail experience (e.g., a tab or link in
   `FighterDetailPageClient`) to the odds page

**Deliverables:**
- `frontend/src/types/odds.ts`
- `frontend/src/lib/api.ts` (typed `getFighterOddsHistory` / `getFighterOddsChart` helpers)
- `frontend/src/hooks/useOddsData.ts` (hooks delegating to the typed API helpers)
- `frontend/src/components/FighterOddsChart.tsx`
- `frontend/src/app/fighters/[id]/odds/page.tsx`
- Component tests

**Success Criteria:**
- Chart displays time-series data correctly
- Fight selector updates chart interactively
- Loading and error states handled
- Mobile-responsive design
- Lighthouse score >90

---

### Phase 6: Testing & Documentation (2-3 hours)

**Goal:** Complete test coverage and documentation

**Tasks:**
1. Write end-to-end integration tests
2. Document API endpoints
3. Create developer guide
4. Performance testing

**Deliverables:**
- `tests/integration/test_odds_pipeline.py`
- `docs/api/odds-endpoints.md`
- Performance benchmarks

**Success Criteria:**
- Test coverage >80%
- All API endpoints documented
- E2E tests passing
- Performance benchmarks met

---

### Phase 7: Production Deployment (1-2 hours)

**Goal:** Deploy to production with monitoring

**Tasks:**
1. Create production deployment script
2. Run data load in production
3. Verify data integrity
4. Monitor for errors
5. Update API documentation

**Deliverables:**
- `scripts/production_odds_load.sh`
- Deployment checklist
- Monitoring dashboard

**Success Criteria:**
- All 13,838 records loaded successfully
- API endpoints accessible publicly
- Frontend deployed and functional
- Zero errors in first 24 hours
- Response times meet SLA

---

## Database Schema

### FighterOdds Model

```python
class FighterOdds(Base):
    """
    Betting odds history from BestFightOdds.com.

    Each record represents odds data for one fighter in one fight.
    The opponent will have a separate record with their odds.
    """
    __tablename__ = "fighter_odds"
    __table_args__ = (
        # Indexes for common queries
        Index("ix_fighter_odds_fighter_id", "fighter_id"),
        Index("ix_fighter_odds_event_date", "event_date"),
        Index("ix_fighter_odds_quality", "data_quality_tier"),
        Index(
            "ix_fighter_odds_fighter_opponent",
            "fighter_id",
            "opponent_name"
        ),

        # Prevent duplicates
        UniqueConstraint(
            "fighter_id",
            "opponent_name",
            "event_name",
            name="uq_fighter_odds_fight"
        ),
    )

    # Primary key
    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        comment="Format: odds_{md5(fighter_id|opponent|event)}"
    )

    # Fighter reference
    fighter_id: Mapped[str] = mapped_column(
        ForeignKey("fighters.id"),
        nullable=False,
        index=True,
        comment="Foreign key to fighters table (UFC Stats ID)"
    )

    # Fight metadata
    opponent_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Opponent name as recorded on BFO"
    )
    event_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Event name from BFO"
    )
    event_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="BFO event page URL"
    )
    event_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
        comment="Date of the event (extracted or null)"
    )

    # Odds data
    opening_odds: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Opening odds (American format, e.g. '+275')"
    )
    closing_range_start: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Start of closing odds range"
    )
    closing_range_end: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="End of closing odds range"
    )

    # Time-series data (JSON array)
    mean_odds_history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="""
        Array of {timestamp_ms, timestamp, odds} data points.
        Example: [
            {
                "timestamp_ms": 1753455870000,
                "timestamp": "2025-07-25T15:04:30.000Z",
                "odds": 3.75
            },
            ...
        ]
        """
    )
    num_odds_points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        index=True,
        comment="Number of data points in time series"
    )

    # Data quality metadata
    data_quality_tier: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
        comment="""
        Quality tier based on data point count:
        - excellent: >50 points
        - good: 30-50 points
        - usable: 10-30 points
        - poor: 1-10 points
        - no_data: 0 points
        """
    )
    is_duplicate: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Flagged as duplicate record (for debugging)"
    )

    # Scraping metadata
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="When this data was scraped from BFO"
    )
    bfo_fighter_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="BFO fighter page URL for re-scraping"
    )

    # Relationships
    fighter: Mapped["Fighter"] = relationship("Fighter")
```

**Schema constraints and invariants:**

- `data_quality_tier` is constrained to one of:
  `{"excellent", "good", "usable", "poor", "no_data"}`.
- The cleaning pipeline ensures `num_odds_points == len(mean_odds_history)` for all loaded rows.
- For v1, all rows written to `fighter_odds` have `is_duplicate = False`; the column and the
  uniqueness constraint on `(fighter_id, opponent_name, event_name)` exist as defensive guards and
  for potential future incremental loaders.

### Migration Template

```python
"""add_fighter_odds_table

Revision ID: XXXXXX
Revises: 805e2f7ba7ce
Create Date: 2025-11-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'XXXXXX'
down_revision = '805e2f7ba7ce'
branch_labels = None
depends_on = None


def upgrade():
    # Create fighter_odds table
    op.create_table(
        'fighter_odds',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('fighter_id', sa.String(), nullable=False),
        sa.Column('opponent_name', sa.String(length=255), nullable=False),
        sa.Column('event_name', sa.String(length=255), nullable=False),
        sa.Column('event_url', sa.String(length=512), nullable=True),
        sa.Column('event_date', sa.Date(), nullable=True),
        sa.Column('opening_odds', sa.String(length=20), nullable=True),
        sa.Column('closing_range_start', sa.String(length=20), nullable=True),
        sa.Column('closing_range_end', sa.String(length=20), nullable=True),
        sa.Column('mean_odds_history', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('num_odds_points', sa.Integer(), nullable=False),
        sa.Column('data_quality_tier', sa.String(length=20), nullable=True),
        sa.Column('is_duplicate', sa.Boolean(), nullable=False),
        sa.Column('scraped_at', sa.DateTime(), nullable=False),
        sa.Column('bfo_fighter_url', sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(['fighter_id'], ['fighters.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fighter_id', 'opponent_name', 'event_name', name='uq_fighter_odds_fight'),
        sa.CheckConstraint(
            "data_quality_tier IN ('excellent','good','usable','poor','no_data') OR data_quality_tier IS NULL",
            name='ck_fighter_odds_quality_tier',
        ),
    )

    # Create indexes
    op.create_index('ix_fighter_odds_fighter_id', 'fighter_odds', ['fighter_id'])
    op.create_index('ix_fighter_odds_event_date', 'fighter_odds', ['event_date'])
    op.create_index('ix_fighter_odds_quality', 'fighter_odds', ['data_quality_tier'])
    op.create_index('ix_fighter_odds_fighter_opponent', 'fighter_odds', ['fighter_id', 'opponent_name'])


def downgrade():
    op.drop_index('ix_fighter_odds_fighter_opponent', table_name='fighter_odds')
    op.drop_index('ix_fighter_odds_quality', table_name='fighter_odds')
    op.drop_index('ix_fighter_odds_event_date', table_name='fighter_odds')
    op.drop_index('ix_fighter_odds_fighter_id', table_name='fighter_odds')
    op.drop_table('fighter_odds')
```

### Index Strategy

| Index | Columns | Purpose | Estimated Selectivity |
|-------|---------|---------|----------------------|
| PRIMARY KEY | id | Unique lookup | 1:1 |
| ix_fighter_odds_fighter_id | fighter_id | Fighter's odds history | 1:11 (avg 11 fights) |
| ix_fighter_odds_event_date | event_date | Timeline queries | 1:50 (fights per date) |
| ix_fighter_odds_quality | data_quality_tier | Filter by quality | 1:2800 (5 tiers) |
| ix_fighter_odds_fighter_opponent | fighter_id, opponent_name | Specific matchup | 1:1 (composite) |
| uq_fighter_odds_fight | fighter_id, opponent_name, event_name | Prevent duplicates | 1:1 (unique) |

**Expected Performance:**
- Fighter odds history query: <50ms
- Quality filtering: <100ms
- Full table scan (stats): <500ms

### Design Decision: JSON Time-Series

- Time-series odds data is stored as a JSON array (`mean_odds_history`) on each `fighter_odds`
  row rather than in a separate “odds_points” table.
- Given the current scale (≈14k rows, tens–hundreds of points per fight), this keeps the
  schema simple while still meeting query latency targets for fighter-level histories and quality
  statistics.
- If future analytics require querying individual odds points across fights (e.g., intraday line
  movement trends across the roster), we can introduce a dedicated, indexed child table and
  backfill from `mean_odds_history` without breaking the existing API contracts.

---

## Data Pipeline

### Fighter and Event Identity Mapping

The cleaned odds data must align with existing domain entities so that odds can be joined reliably
with fighter and event views.

- **Fighters**
  - Each raw record carries a `fighter_id` that is expected to match `fighters.id`
    (UFC Stats ID) in the main database.
  - During cleaning, we validate that every record’s `fighter_id` exists in the `fighters`
    table (or in the canonical fixtures used to seed it).
  - Records whose `fighter_id` cannot be resolved are written to
    `data/processed/bfo_fighter_mean_odds_unmatched.jsonl` and **excluded** from the cleaned file
    and database load.
  - This ensures that all loaded odds rows satisfy the foreign key constraint and eliminates the
    “Fighter ID mismatch” risk in production.

- **Events**
  - Odds records include `event_name` and `event_url` from BestFightOdds; these fields are stored
    as denormalised text in `fighter_odds` (no hard FK to the `events` table).
  - Where possible, the loading pipeline derives `event_date` from BFO archive data; when the date
    cannot be inferred, `event_date` is left `NULL`.
  - Future iterations can tighten this by introducing an explicit FK to the `events` table once
    cross-promotion event mapping is stable.

### Cleaning Pipeline

**Script:** `scripts/clean_bfo_fighter_mean_odds.py`

**Inputs:**
- `data/raw/bfo_fighter_mean_odds.jsonl` (14,054 records)

**Outputs:**
- `data/processed/bfo_fighter_mean_odds_clean.jsonl` (13,838 records)
- `data/processed/bfo_odds_cleaning_stats.json` (statistics)

**Processing Steps:**

1. **Load Raw Data**
   ```python
   records = []
   with open('data/raw/bfo_fighter_mean_odds.jsonl') as f:
       for line in f:
           records.append(json.loads(line))
   # 14,054 records loaded
   ```

2. **Detect Duplicates**
   ```python
   def generate_fight_key(record):
       return f"{record['fighter_id']}|{record['opponent_name']}|{record['event_name']}"

   fight_groups: dict[str, list[dict]] = {}
   for record in records:
       key = generate_fight_key(record)
       fight_groups.setdefault(key, []).append(record)

   duplicates = {key: group for key, group in fight_groups.items() if len(group) > 1}

   # Found 216 duplicate records in 108 groups
   ```

3. **Select Best Duplicates**
   ```python
   def select_best_duplicate(records):
       # Sort by:
       # 1. Most data points (desc)
       # 2. Most recent scrape (desc)
       return sorted(records, key=lambda r: (
           -r.get('num_odds_points', 0),
           r.get('scraped_at', '')
       ))[0]
   ```

   After selection, only the single best record for each `(fighter_id, opponent_name, event_name)`
   key is kept in the cleaned dataset; all other duplicates are discarded before the load step.

4. **Normalize Format**
   ```python
   def normalize_odds_format(record):
       if 'mean_odds_values' in record:
           # Old format: {time, odds}
           old_values = record.pop('mean_odds_values')
           new_history = [
               {
                   'timestamp_ms': pt['time'],
                   'timestamp': datetime.fromtimestamp(pt['time']/1000).isoformat()+'Z',
                   'odds': pt['odds']
               }
               for pt in old_values
           ]
           record['mean_odds_history'] = new_history
       return record

   # Normalized 78 old-format records
   ```

5. **Assign Quality Tiers**
   ```python
   def calculate_quality_tier(num_points):
       if num_points > 50:
           return 'excellent'
       elif num_points >= 30:
           return 'good'
       elif num_points >= 10:
           return 'usable'
       elif num_points > 0:
           return 'poor'
       else:
           return 'no_data'

   for record in records:
       record['data_quality_tier'] = calculate_quality_tier(
           record.get('num_odds_points', 0)
       )
   ```

6. **Validate Structure**
   ```python
   def validate_odds_record(record):
       required = ['fighter_id', 'opponent_name', 'event_name', 'mean_odds_history']
       for field in required:
           if field not in record:
               return False, f"Missing {field}"

       for i, point in enumerate(record['mean_odds_history']):
           if 'timestamp_ms' not in point or 'odds' not in point:
               return False, f"Invalid data point {i}"

       return True, None

   # Validation errors: 0
   ```

**Expected Cleaning Stats:**

```json
{
  "input_records": 14054,
  "duplicates_removed": 216,
  "old_format_normalized": 78,
  "invalid_records": 0,
  "output_records": 13838,
  "quality_distribution": {
    "excellent": 6327,
    "good": 3500,
    "usable": 2400,
    "poor": 1594,
    "no_data": 17
  }
}
```

---

### Loading Pipeline

**Script:** `scripts/load_bfo_fighter_odds.py`

**Inputs:**
- `data/processed/bfo_fighter_mean_odds_clean.jsonl` (13,838 records)

**Process:**

1. **Parse Records**
   ```python
   def parse_odds_record(record):
       odds_id = generate_odds_id(record)  # odds_{md5(key)}

       return {
           'id': odds_id,
           'fighter_id': record['fighter_id'],
           'opponent_name': record['opponent_name'],
           'event_name': record['event_name'],
           'event_url': record.get('event_url'),
           'event_date': None,  # TODO: Extract from event_name
           'opening_odds': record.get('opening_odds'),
           'closing_range_start': record.get('closing_range_start'),
           'closing_range_end': record.get('closing_range_end'),
           'mean_odds_history': record.get('mean_odds_history', []),
           'num_odds_points': record.get('num_odds_points', 0),
           'data_quality_tier': record.get('data_quality_tier'),
           'is_duplicate': False,
           'scraped_at': parse_timestamp(record.get('scraped_at')),
           'bfo_fighter_url': record.get('fighter_url'),
       }
   ```

2. **Bulk Insert**
   ```python
   async def bulk_insert_odds(records, batch_size=100):
       for i in range(0, len(records), batch_size):
           batch = records[i:i+batch_size]

           # PostgreSQL INSERT ... ON CONFLICT DO NOTHING
           stmt = insert(FighterOdds).values(batch)
           stmt = stmt.on_conflict_do_nothing(
               constraint='uq_fighter_odds_fight'
           )

           result = await session.execute(stmt)
           await session.commit()

           print(f"Batch {i//batch_size + 1}: {result.rowcount} inserted")
   ```

3. **Progress Tracking**
   ```
   Batch 1/139: 100 inserted
   Batch 2/139: 100 inserted
   ...
   Batch 139/139: 38 inserted

   Total: 13,838 inserted, 0 skipped
   ```

**Expected Load Time:** 2-3 minutes for 13,838 records

---

### Idempotency & Resume Behavior

- The cleaning script always rewrites `data/processed/bfo_fighter_mean_odds_clean.jsonl` from the
  raw source file, ensuring a single canonical view of the odds dataset per run.
- The loader uses `INSERT ... ON CONFLICT DO NOTHING` against the
  `uq_fighter_odds_fight (fighter_id, opponent_name, event_name)` constraint. Re-running the load
  with the same cleaned file is therefore safe and results in `0` newly inserted rows.
- If scrapers are re-run and new or corrected odds are produced, those changes appear as a new
  cleaned file; subsequent loads will only insert truly new `(fighter, opponent, event)` keys.
- If we ever need to perform in-place corrections for existing fights, we can introduce an explicit
  “upsert” path (DELETE + fresh INSERT for the affected keys) as a separate maintenance workflow.

## API Design

### Endpoints

#### 1. Get Fighter Odds History

```http
GET /api/odds/fighter/{fighter_id}
```

**Description:** Get betting odds history for a fighter across all fights.

**Parameters:**
- `fighter_id` (path, required): Fighter ID from UFC Stats
- `limit` (query, optional): Max records to return (default: 100, max: 500)
- `quality_min` (query, optional): Minimum quality tier (e.g., "usable")

**Response:**
```json
{
  "fighter_id": "7492",
  "total_fights": 25,
  "returned": 20,
  "odds_history": [
    {
      "id": "odds_abc123",
      "opponent_name": "Islam Makhachev",
      "event_name": "UFC 322",
      "event_date": "2025-09-15",
      "opening_odds": "+275",
      "closing_range": {
        "start": "+210",
        "end": "+230"
      },
      "num_odds_points": 93,
      "data_quality": "excellent"
    }
  ]
}
```

**Caching:** 5 minutes
**Expected Response Time:** <100ms (p99)

**No-data semantics:**
- If the fighter exists in the `fighters` table but we have **no odds records**, the endpoint
  returns `200 OK` with:
  - `total_fights = 0`
  - `returned = 0`
  - `odds_history = []`
- If the fighter does **not** exist in the `fighters` table, the endpoint returns `404` as
  described in the Error Handling section.

---

#### 2. Get Fighter Odds Chart Data

```http
GET /api/odds/fighter/{fighter_id}/chart
```

**Description:** Get chart-ready odds time-series data for visualization.

**Parameters:**
- `fighter_id` (path, required): Fighter ID
- `limit` (query, optional): Max fights to return (default: 20)

**Response:**
```json
{
  "fighter_id": "7492",
  "fights": [
    {
      "fight_id": "odds_abc123",
      "opponent": "Islam Makhachev",
      "event": "UFC 322",
      "event_date": "2025-09-15",
      "opening_odds": "+275",
      "closing_odds": "+230",
      "time_series": [
        {
          "timestamp_ms": 1753455870000,
          "timestamp": "2025-07-25T15:04:30.000Z",
          "odds": 3.75
        }
      ],
      "quality": "excellent"
    }
  ]
}
```

**Caching:** 10 minutes
**Expected Response Time:** <150ms (p99)

---

#### 3. Get Fight Odds Detail

```http
GET /api/odds/fight/{odds_id}
```

**Description:** Get detailed odds data for a specific fight, including full time-series.

**Response:**
```json
{
  "id": "odds_abc123",
  "fighter_id": "7492",
  "opponent_name": "Islam Makhachev",
  "event_name": "UFC 322",
  "event_date": "2025-09-15",
  "event_url": "https://www.bestfightodds.com/events/ufc-322-3830",
  "opening_odds": "+275",
  "closing_range": {
    "start": "+210",
    "end": "+230"
  },
  "mean_odds_history": [...],
  "num_odds_points": 93,
  "data_quality": "excellent",
  "scraped_at": "2025-11-13T00:10:10.564Z"
}
```

**Caching:** 15 minutes
**Expected Response Time:** <50ms (p99)

---

#### 4. Get Odds Quality Statistics

```http
GET /api/odds/stats/quality
```

**Description:** Get dataset quality statistics and coverage metrics.

**Response:**
```json
{
  "total_records": 13838,
  "unique_fighters": 1255,
  "quality_distribution": {
    "excellent": 6327,
    "good": 3500,
    "usable": 2400,
    "poor": 1594,
    "no_data": 17
  },
  "avg_odds_points": 78.4,
  "coverage_stats": {
    "fighters_with_odds": 1255,
    "total_fighters": 1262,
    "coverage_percentage": 99.4
  }
}
```

**Caching:** 1 hour
**Expected Response Time:** <200ms (p99)

---

### Error Handling

| Status Code | Scenario | Response |
|-------------|----------|----------|
| 200 | Success | Data returned |
| 400 | Invalid parameters | `{"detail": "Invalid quality tier"}` |
| 404 | Fighter not found in fighters table | `{"detail": "Fighter not found"}` |
| 500 | Database error | `{"detail": "Internal server error"}` |
| 503 | Cache unavailable | Data still returned, warning logged |

### Schema Contracts

- Canonical response schemas for these endpoints live in `backend/schemas/odds.py` and are exposed
  via OpenAPI; the JSON examples in this document mirror those Pydantic models.
- Frontend TypeScript types for odds responses are defined in `frontend/src/types/odds.ts` and map
  directly from the API’s snake_case fields (e.g., `data_quality_tier` → `data_quality` where
  appropriate).
- Any changes to field names or structures must be reflected in both the Pydantic schemas and the
  TypeScript types to keep end-to-end type safety intact.

---

## Frontend Components

### Component Hierarchy

```
FighterOddsPage
├── FighterOddsChart          (Main chart component)
│   ├── ResponsiveContainer
│   ├── LineChart (Recharts)
│   │   ├── XAxis (timestamp)
│   │   ├── YAxis (odds)
│   │   ├── CartesianGrid
│   │   ├── Tooltip
│   │   └── Line (mean odds)
│   └── QualityIndicator
└── FightSelector              (List of fights)
    └── FightSelectorItem[]
```

### Key Components

#### 1. FighterOddsChart

**File:** `frontend/src/components/FighterOddsChart.tsx`

**Props:**
```typescript
interface FighterOddsChartProps {
  fights: FightOdds[];
  selectedFightId?: string;
  onFightSelect?: (fightId: string) => void;
}
```

**Features:**
- Responsive Recharts line chart
- Interactive timeline with zoom/pan
- Opening/closing odds markers
- Quality tier indicators
- Data point count display

**State Management:**
```typescript
const [selectedFight, setSelectedFight] = useState<FightOdds | null>(null);
const chartData = useMemo(() => {
  if (!selectedFight) return [];
  return selectedFight.time_series.map(pt => ({
    timestamp: new Date(pt.timestamp_ms).toLocaleDateString(),
    odds: pt.odds,
    date: new Date(pt.timestamp_ms)
  }));
}, [selectedFight]);
```

---

#### 2. useOddsData Hook

**File:** `frontend/src/hooks/useOddsData.ts`

```typescript
import { useQuery } from "@tanstack/react-query";

import type { ApiError } from "@/lib/errors";
import { getFighterOddsChart, getFighterOddsHistory } from "@/lib/api";

export function useOddsChart(fighterId: string | undefined) {
  return useQuery<OddsChartData, ApiError>({
    queryKey: ["odds", "chart", fighterId],
    queryFn: () => getFighterOddsChart(fighterId!),
    enabled: !!fighterId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useOddsHistory(fighterId: string | undefined) {
  return useQuery<OddsHistory, ApiError>({
    queryKey: ["odds", "history", fighterId],
    queryFn: () => getFighterOddsHistory(fighterId!),
    enabled: !!fighterId,
    staleTime: 5 * 60 * 1000,
  });
}
```

---

#### 3. Odds Page

**File:** `frontend/src/app/fighters/[id]/odds/page.tsx`

**Layout:**
```tsx
export default function FighterOddsPage() {
  const { id } = useParams();
  const { data: chartData, isLoading } = useOddsChart(id);
  const [selectedFight, setSelectedFight] = useState<string>();

  if (isLoading) return <Skeleton />;
  if (!chartData?.fights?.length) return <EmptyState />;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Betting Odds History</CardTitle>
        </CardHeader>
        <CardContent>
          <FighterOddsChart
            fights={chartData.fights}
            selectedFightId={selectedFight}
            onFightSelect={setSelectedFight}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>All Fights</CardTitle>
        </CardHeader>
        <CardContent>
          <FightSelector
            fights={chartData.fights}
            selected={selectedFight}
            onSelect={setSelectedFight}
          />
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## Testing Strategy

### Test Coverage Goals

| Layer | Target Coverage | Critical Paths |
|-------|----------------|----------------|
| Models | 100% | Model instantiation, validation, relationships |
| Repositories | 90% | All query methods, error handling |
| Services | 85% | Business logic, caching, transformations |
| API | 80% | All endpoints, error codes, edge cases |
| Frontend | 70% | Components, hooks, user interactions |

### Test Types

#### 1. Unit Tests

**Models:**
```python
# tests/backend/test_odds_model.py
def test_fighter_odds_model_creation():
    odds = FighterOdds(
        id="odds_test",
        fighter_id="7492",
        opponent_name="Test",
        event_name="Test Event",
        mean_odds_history=[],
        num_odds_points=0
    )
    assert odds.fighter_id == "7492"

def test_quality_tier_validation():
    # Test valid tiers
    for tier in ['excellent', 'good', 'usable', 'poor', 'no_data']:
        odds = FighterOdds(data_quality_tier=tier)
        assert odds.data_quality_tier == tier
```

**Repositories:**
```python
# tests/backend/test_odds_repository.py
@pytest.mark.asyncio
async def test_get_fighter_odds_history(db_session, sample_odds):
    repo = OddsRepository(db_session)

    # Insert sample data
    await repo.bulk_insert_odds([sample_odds])

    # Query
    results = await repo.get_fighter_odds_history("7492", limit=10)

    assert len(results) == 1
    assert results[0].fighter_id == "7492"
    assert results[0].opponent_name == sample_odds['opponent_name']

@pytest.mark.asyncio
async def test_get_quality_stats(db_session):
    repo = OddsRepository(db_session)
    stats = await repo.get_quality_stats()

    assert 'total' in stats
    assert 'quality_distribution' in stats
    assert stats['total'] >= 0
```

**Services:**
```python
# tests/backend/test_odds_service.py
@pytest.mark.asyncio
async def test_odds_service_caching(mock_cache, odds_service):
    # First call - cache miss
    result1 = await odds_service.get_fighter_odds_history("7492")
    assert mock_cache.get.call_count == 1
    assert mock_cache.set.call_count == 1

    # Second call - cache hit
    result2 = await odds_service.get_fighter_odds_history("7492")
    assert mock_cache.get.call_count == 2
    assert mock_cache.set.call_count == 1  # No new cache set

    assert result1 == result2
```

---

#### 2. Integration Tests

**API Endpoints:**
```python
# tests/backend/test_odds_api.py
@pytest.mark.asyncio
async def test_get_fighter_odds_history_endpoint(test_client, db_with_odds):
    response = test_client.get("/api/odds/fighter/7492")

    assert response.status_code == 200
    data = response.json()

    assert "fighter_id" in data
    assert "total_fights" in data
    assert "odds_history" in data
    assert isinstance(data['odds_history'], list)

@pytest.mark.asyncio
async def test_get_fighter_odds_404(test_client):
    response = test_client.get("/api/odds/fighter/nonexistent")
    assert response.status_code == 404
    assert "detail" in response.json()
```

**End-to-End:**
```python
# tests/integration/test_odds_pipeline.py
@pytest.mark.integration
async def test_complete_odds_pipeline():
    """
    Test complete flow:
    1. Clean raw data
    2. Load into database
    3. Query via repository
    4. Fetch via API
    5. Verify data integrity
    """
    # Step 1: Clean
    from scripts.clean_bfo_fighter_mean_odds import clean_odds_record
    raw = load_sample_raw_data()
    cleaned = [clean_odds_record(r) for r in raw]

    # Step 2: Load
    from scripts.load_bfo_fighter_odds import load_odds_batch
    repo = OddsRepository(test_db)
    inserted = await load_odds_batch(cleaned, repo)
    assert inserted == len(cleaned)

    # Step 3: Query
    results = await repo.get_fighter_odds_history("test_fighter")
    assert len(results) > 0

    # Step 4: API
    response = test_client.get("/api/odds/fighter/test_fighter")
    assert response.status_code == 200

    # Step 5: Verify
    api_data = response.json()
    db_data = results[0]
    assert api_data['odds_history'][0]['opponent_name'] == db_data.opponent_name
```

---

#### 3. Performance Tests

**Query Performance:**
```python
# tests/performance/test_odds_performance.py
@pytest.mark.performance
async def test_fighter_odds_history_performance(db_with_large_dataset):
    """Verify fighter odds history query meets SLA (<100ms)."""
    repo = OddsRepository(db_with_large_dataset)

    import time
    start = time.perf_counter()

    results = await repo.get_fighter_odds_history("7492", limit=100)

    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 100, f"Query took {elapsed_ms:.1f}ms (SLA: <100ms)"
    assert len(results) > 0

@pytest.mark.performance
async def test_bulk_insert_performance():
    """Verify bulk insert handles 10,000 records in <30s."""
    import time

    records = generate_sample_odds(10_000)

    start = time.perf_counter()
    await bulk_insert_odds(records, batch_size=100)
    elapsed = time.perf_counter() - start

    assert elapsed < 30, f"Bulk insert took {elapsed:.1f}s (SLA: <30s)"
```

---

#### 4. Frontend Tests

**Component Tests:**
```typescript
// tests/components/FighterOddsChart.test.tsx
import { render, screen } from '@testing-library/react';
import { FighterOddsChart } from '@/components/FighterOddsChart';

describe('FighterOddsChart', () => {
  it('renders chart with time-series data', () => {
    const fights = [
      {
        fight_id: 'test1',
        opponent: 'Test Opponent',
        time_series: [
          { timestamp_ms: 123, odds: 2.5 }
        ]
      }
    ];

    render(<FighterOddsChart fights={fights} />);

    expect(screen.getByText('vs Test Opponent')).toBeInTheDocument();
  });

  it('shows empty state when no data', () => {
    render(<FighterOddsChart fights={[]} />);
    expect(screen.getByText(/no odds data/i)).toBeInTheDocument();
  });
});
```

**Hook Tests:**
```typescript
// tests/hooks/useOddsData.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { useOddsChart } from '@/hooks/useOddsData';

describe('useOddsChart', () => {
  it('fetches odds chart data', async () => {
    const { result } = renderHook(() => useOddsChart('7492'));

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveProperty('fighter_id', '7492');
    expect(result.current.data?.fights).toBeInstanceOf(Array);
  });
});
```

---

## Deployment Plan

### Pre-Deployment Checklist

**Code Quality:**
- [ ] All tests passing (unit, integration, E2E)
- [ ] Test coverage >80%
- [ ] Linting passing (no warnings)
- [ ] Type checking passing (mypy, TypeScript)
- [ ] No security vulnerabilities (pip audit, npm audit)

**Database:**
- [ ] Migration tested on staging database
- [ ] Indexes created and verified
- [ ] Foreign key constraints validated
- [ ] Backup strategy confirmed

**Performance:**
- [ ] API response times meet SLA
- [ ] Database query performance validated
- [ ] Caching strategy tested
- [ ] Frontend Lighthouse score >90

**Documentation:**
- [ ] API documentation complete
- [ ] OpenAPI specs updated
- [ ] Developer guide written
- [ ] Deployment runbook ready

---

### Deployment Steps

#### 1. Database Migration (5 minutes)

```bash
# Backup production database
pg_dump -h $PROD_DB_HOST -U $PROD_DB_USER -d ufc_pokedex \
  -Fc -f "backups/pre_odds_$(date +%Y%m%d_%H%M%S).dump"

# Apply migration
cd backend
alembic upgrade head

# Verify migration
psql -h $PROD_DB_HOST -U $PROD_DB_USER -d ufc_pokedex \
  -c "\d fighter_odds"
```

**Rollback Plan:**
```bash
# If migration fails
alembic downgrade -1

# Restore backup if needed
pg_restore -h $PROD_DB_HOST -U $PROD_DB_USER -d ufc_pokedex \
  backups/pre_odds_YYYYMMDD_HHMMSS.dump
```

---

#### 2. Data Load (10-15 minutes)

```bash
# Clean data (if not already done)
python scripts/clean_bfo_fighter_mean_odds.py \
  --input data/raw/bfo_fighter_mean_odds.jsonl \
  --output data/processed/bfo_fighter_mean_odds_clean.jsonl

# Verify clean data
wc -l data/processed/bfo_fighter_mean_odds_clean.jsonl
# Expected: 13838

# Load into production database
DATABASE_URL=$PROD_DATABASE_URL \
python scripts/load_bfo_fighter_odds.py \
  --input data/processed/bfo_fighter_mean_odds_clean.jsonl \
  --batch-size 100

# Verify data
psql -h $PROD_DB_HOST -U $PROD_DB_USER -d ufc_pokedex -c "
SELECT
  COUNT(*) as total,
  COUNT(DISTINCT fighter_id) as unique_fighters,
  data_quality_tier,
  COUNT(*) as tier_count
FROM fighter_odds
GROUP BY data_quality_tier
ORDER BY tier_count DESC;
"

# Expected:
# total: 13838
# unique_fighters: 1255
# Quality distribution matching dev
```

---

#### 3. Backend Deployment (Railway)

```bash
# Deploy backend
git push railway master

# Monitor deployment
railway logs --tail

# Verify health
curl https://api.ufc.wolfgangschoenberger.com/health
# Expected: {"status": "healthy"}

# Test odds endpoints
curl https://api.ufc.wolfgangschoenberger.com/api/odds/fighter/7492 | jq .
curl https://api.ufc.wolfgangschoenberger.com/api/odds/stats/quality | jq .
```

---

#### 4. Frontend Deployment (Vercel)

```bash
# Deploy frontend
cd frontend
vercel deploy --prod

# Verify deployment
curl https://ufc.wolfgangschoenberger.com/fighters/7492/odds

# Test in browser
open https://ufc.wolfgangschoenberger.com/fighters/7492/odds
```

---

#### 5. Post-Deployment Validation (15 minutes)

**API Validation:**
```bash
# Test each endpoint
curl https://api.ufc.wolfgangschoenberger.com/api/odds/fighter/7492
curl https://api.ufc.wolfgangschoenberger.com/api/odds/fighter/7492/chart
curl https://api.ufc.wolfgangschoenberger.com/api/odds/stats/quality

# Check response times
ab -n 100 -c 10 https://api.ufc.wolfgangschoenberger.com/api/odds/fighter/7492
# Expect: 95% < 200ms
```

**Frontend Validation:**
```bash
# Lighthouse audit
lighthouse https://ufc.wolfgangschoenberger.com/fighters/7492/odds --output=json
# Expect: Performance >90, Accessibility >95

# Visual regression
# (Manual check in browser)
```

**Database Validation:**
```sql
-- Check data integrity
SELECT
  COUNT(*) as total_records,
  COUNT(DISTINCT fighter_id) as unique_fighters,
  AVG(num_odds_points) as avg_data_points,
  MIN(scraped_at) as oldest_scrape,
  MAX(scraped_at) as newest_scrape
FROM fighter_odds;

-- Check index usage
EXPLAIN ANALYZE
SELECT * FROM fighter_odds
WHERE fighter_id = '7492'
ORDER BY event_date DESC
LIMIT 100;
-- Expect: Index Scan on ix_fighter_odds_fighter_id
```

---

### Monitoring

**Metrics to Track:**

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| API Response Time (p99) | <200ms | >500ms |
| Database Query Time (p99) | <100ms | >300ms |
| Cache Hit Rate | >80% | <60% |
| Error Rate | <0.1% | >1% |
| Frontend Load Time (p75) | <2s | >5s |

**Dashboards:**
- Backend: Railway metrics + custom APM wired via `backend/monitoring.py` (FastAPI middleware and
  structured logging for odds endpoints)
- Database: PostgreSQL `pg_stat_statements` plus ad-hoc `EXPLAIN ANALYZE` checks for
  `fighter_odds` queries
- Frontend: Vercel Analytics + Lighthouse CI, focusing on the `/fighters/[id]/odds` route
- Errors: Sentry (if configured) with tags/contexts for odds-related routes and services

**Alerts:**
- Response time degradation
- Error rate spike
- Database connection issues
- Cache unavailability

---

## Success Criteria

### Functional Requirements

**Database:**
- [x] `fighter_odds` table created with all columns
- [x] 13,838 records loaded successfully
- [x] 1,255 unique fighters covered
- [x] All indexes created and used by query planner
- [x] Foreign key constraints enforced

**API:**
- [x] All 4 endpoints functional and documented
- [x] Pagination working correctly
- [x] Error handling (404, 500) implemented
- [x] Caching strategy active
- [x] OpenAPI documentation complete

**Frontend:**
- [x] Odds chart displays time-series data
- [x] Fight selector interactive
- [x] Quality indicators visible
- [x] Loading and error states handled
- [x] Mobile-responsive design

**Testing:**
- [x] Test coverage >80%
- [x] All tests passing
- [x] Integration tests validate end-to-end flow
- [x] Performance tests meet SLA

---

### Non-Functional Requirements

**Performance:**
- API response times <200ms (p99)
- Database query times <100ms (p99)
- Frontend load time <2s (p75)
- Bulk insert rate >500 records/second

**Reliability:**
- Error rate <0.1%
- Cache hit rate >80%
- Database connection pool stable
- No memory leaks

**Maintainability:**
- Code follows existing patterns
- Documentation complete
- Tests cover critical paths
- Monitoring in place

**Security:**
- No SQL injection vulnerabilities
- Input validation on all endpoints
- Rate limiting configured
- Sensitive data not logged

---

## Risk Mitigation

### Identified Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Migration fails in production | High | Low | Test on staging, have rollback plan |
| Data load timeout | Medium | Medium | Batch processing, resume capability |
| Performance degradation | High | Low | Load testing, index optimization |
| Cache unavailability | Medium | Low | In-memory fallback implemented |
| Duplicate data post-load | Low | Low | Unique constraint prevents duplicates |
| Fighter ID mismatch | Medium | Low | Validate against fighters table |

### Rollback Procedures

**Database Rollback:**
```bash
# Rollback migration
alembic downgrade -1

# Or restore backup
pg_restore -h $PROD_DB_HOST -U $PROD_DB_USER -d ufc_pokedex \
  -c backups/pre_odds_YYYYMMDD.dump
```

**Application Rollback:**
```bash
# Railway
railway rollback

# Vercel
vercel rollback
```

**Data Rollback:**
```sql
-- Remove all odds data
DELETE FROM fighter_odds;

-- Verify
SELECT COUNT(*) FROM fighter_odds;
-- Expected: 0
```

---

## Handoff Notes

### For the Next Developer

**What's Already Done:**
1. ✅ Scrapers are complete and tested (8 BFO spiders)
2. ✅ 14,054 odds records scraped and stored in `data/raw/`
3. ✅ Data quality analysis complete
4. ✅ Bookmaker mapping infrastructure exists
5. ✅ Architectural patterns established (see codebase review)

**What You Need to Build:**
1. ❌ Database schema (follow spec in this doc)
2. ❌ Data cleaning pipeline (remove dupes, normalize)
3. ❌ Data loading pipeline (bulk insert with progress)
4. ❌ Repository layer (queries with caching)
5. ❌ API endpoints (4 endpoints, OpenAPI docs)
6. ❌ Frontend components (chart + page)
7. ❌ Tests (unit, integration, E2E)

**Key Files to Start With:**
1. `backend/db/models/__init__.py` - Add FighterOdds model
2. `scripts/clean_bfo_fighter_mean_odds.py` - Create cleaning pipeline
3. `backend/db/repositories/odds.py` - Create repository
4. `backend/api/odds.py` - Create API endpoints
5. `frontend/src/components/FighterOddsChart.tsx` - Create chart

**Dependencies:**
- All scrapers in `scraper/spiders/bestfightodds_*.py`
- Bookmaker mapping in `scraper/bookmaker_mapping.py`
- Reference implementations:
  - Fighter API: `backend/api/fighters.py`
  - Fighter Service: `backend/services/fighter_query_service.py`
  - Fighter Repository: `backend/db/repositories/fighter/`

**Common Pitfalls:**
1. **Don't** create SQLite-compatible code (PostgreSQL only)
2. **Don't** skip migration testing
3. **Don't** forget to register new routes in `backend/api/__init__.py`
4. **Don't** skip cache key functions in services
5. **Do** follow async patterns throughout
6. **Do** use dependency injection for services
7. **Do** add comprehensive error handling
8. **Do** write tests before considering a phase complete

**Questions? Check:**
- Codebase review: `BFO_ODDS_INTEGRATION_CODEBASE_REVIEW.md`
- BFO scraper docs: `docs/BETTING_ODDS_SCRAPER.md`
- This spec: You're reading it!

---

**Document Version:** 1.0
**Last Updated:** 2025-11-13
**Author:** UFC Pokedex Engineering Team
**Status:** Ready for Implementation

11/13/2025 05:58 PM
