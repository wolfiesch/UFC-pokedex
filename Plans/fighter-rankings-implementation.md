# Fighter Rankings Feature - Implementation Plan

**Created:** 2025-11-09
**Status:** Phase 2 Complete (UFC scraper working), Ready for Phase 3
**Estimated Completion:** ~4-5 days for remaining phases

## Overview

Implement a comprehensive fighter rankings feature that displays:
- **Current UFC rankings** (1-15 or NR for Not Ranked)
- **Peak career ranking** for each fighter
- **Historical ranking trends** over time
- **Multi-source rankings** (UFC.com primary, Fight Matrix for historical data)

## Architecture Decisions

### Data Sources
1. **UFC.com** - Official current rankings (updated weekly)
   - URL: `https://www.ufc.com/rankings`
   - Structure: 11 divisions × 16 fighters (1 champion + 15 ranked)
   - Scraping: Implemented and working ✅

2. **Fight Matrix** - Historical rankings for peak calculations
   - URL: To be determined in Phase 3
   - Purpose: Backfill historical data (12 months)
   - Status: Not started ⏳

### Name Matching Strategy
- **Primary:** Fuzzy matching with rapidfuzz (≥80% confidence threshold)
- **Penalty:** Division mismatch reduces confidence by 10% (0.9x multiplier)
- **Rejection:** Division mismatch that drops below threshold is rejected
- **Below Threshold:** Matches <80% are rejected (no record tiebreaker available)
- **Manual Review:** Operators must manually map fighters in 70-79% confidence range
- **Note:** Rankings sources don't include fighter records, so no record validation possible

### Database Schema

#### `fighter_rankings` Table
```sql
CREATE TABLE fighter_rankings (
    id VARCHAR PRIMARY KEY DEFAULT uuid_generate_v4(),
    fighter_id VARCHAR NOT NULL REFERENCES fighters(id),
    division VARCHAR(50) NOT NULL,
    rank INTEGER NULL,  -- 0=Champion, 1-15=Ranked, NULL=Not Ranked
    previous_rank INTEGER NULL,
    rank_date DATE NOT NULL,
    source VARCHAR(50) NOT NULL,  -- 'ufc', 'fightmatrix', 'tapology'
    is_interim BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint prevents duplicate snapshots
    CONSTRAINT uq_fighter_rankings_natural_key
        UNIQUE (fighter_id, division, rank_date, source)
);

-- Indexes for common queries
CREATE INDEX ix_fighter_rankings_fighter_date ON fighter_rankings(fighter_id, rank_date);
CREATE INDEX ix_fighter_rankings_division_date_source ON fighter_rankings(division, rank_date, source);
CREATE INDEX ix_fighter_rankings_fighter_source ON fighter_rankings(fighter_id, source);
```

**Migrations:**
- ✅ `f143b7233ba8_add_fighter_rankings_table.py` - Initial table creation with UNIQUE constraint

### Rank Storage Convention
- **0** = Champion
- **1-15** = Ranked positions
- **NULL** = Not Ranked (NR)

### UI Display Decisions
- Show "NR" for unranked fighters with peak ranking in parentheses
- Filters: Currently ranked only, by ranking tier (Top 5/10/15)
- Sorting: By current rank or peak rank
- Historical trend charts with Recharts library

---

## Phase 1: Foundation ✅ COMPLETED

**Goal:** Database schema, models, repository, and name matching infrastructure

### Deliverables (All Complete)

1. **Dependencies** ✅
   - rapidfuzz already available (replaces fuzzywuzzy)
   - No additional installs needed

2. **Database Migration** ✅
   - File: `backend/db/migrations/versions/f143b7233ba8_add_fighter_rankings_table.py`
   - File: `backend/db/migrations/versions/0ff38dee59d4_add_unique_constraint_fighter_rankings.py`
   - Status: Ready to apply (requires PostgreSQL running)
   - SQLite: Auto-creates on startup

3. **SQLAlchemy Model** ✅
   - File: `backend/db/models/__init__.py:188-230`
   - Class: `FighterRanking`
   - Includes: Indexes, relationships, UUID auto-generation
   - Fix applied: `id` field now has `default=lambda: str(uuid.uuid4())`

4. **Name Matcher Utility** ✅
   - File: `scraper/utils/name_matcher.py`
   - Class: `FighterNameMatcher`
   - Methods:
     - `match_fighter()` - Single name matching with division verification
     - `match_multiple()` - Batch matching
     - `_boost_confidence_with_record()` - Placeholder (NOT IMPLEMENTED)
   - Fixes applied:
     - Uses tuple list instead of dict to preserve duplicate names
     - Division mismatch re-checks threshold before returning
     - Honest documentation about lack of record validation

5. **Repository** ✅
   - File: `backend/db/repositories/ranking_repository.py`
   - Class: `RankingRepository`
   - Methods:
     - `get_current_rankings(division, source)` - Latest rankings per division
     - `get_peak_ranking(fighter_id, source)` - Best rank ever achieved
     - `get_fighter_ranking_history(fighter_id, source, limit)` - Time series
     - `upsert_ranking(ranking_data)` - Insert or update using natural key

---

## Phase 2: UFC Rankings Scraper ✅ COMPLETED

**Goal:** Scrape current UFC rankings and validate pipeline

### Deliverables (All Complete)

1. **Pydantic Model** ✅
   - File: `scraper/models/fighter.py:103-169`
   - Class: `FighterRankingItem`
   - Fields: fighter_name, fighter_id, division, rank, previous_rank, is_interim, rank_date, source
   - Validators: rank parsing ("C"→0, "NR"→None), confidence clamping
   - Fix applied: Added `item_type` field for pipeline routing

2. **UFC Rankings Parser** ✅
   - File: `scraper/utils/ufc_rankings_parser.py`
   - Function: `parse_ufc_rankings_page(html, rank_date)`
   - Returns: List of ranking dicts (176 entries expected)
   - HTML Structure:
     - `.view-grouping` - Division container
     - `.view-grouping-header::text` - Division name
     - `.rankings--athlete--champion .info a` - Champion
     - `tbody tr` - Ranked fighters (1-15)
     - `td:nth-child(1)::text` - Rank number
     - `td:nth-child(2) a::text` - Fighter name
   - Fix applied: Division names now normalized via `normalize_division_name()`

3. **UFC Rankings Spider** ✅
   - File: `scraper/spiders/ufc_rankings.py`
   - Name: `ufc_rankings`
   - URL: `https://www.ufc.com/rankings`
   - Output: FighterRankingItem instances
   - Status: Successfully scraped 176 rankings (11 divisions × 16 fighters)

4. **Validation Pipeline Fix** ✅
   - File: `scraper/pipelines/validation.py`
   - Added routing for `item_type="fighter_ranking"` → `FighterRankingItem`
   - Now handles ranking items correctly

5. **Testing** ✅
   - Ran spider against live UFC.com
   - Verified: 176 total rankings
   - Verified: 11 divisions (8 men's + 3 women's)
   - Verified: Each division has 16 fighters (1 champion + 15 ranked)
   - Output: `/tmp/claude/ufc_rankings_final.json`

### Test Results
```
Divisions scraped:
  16 Bantamweight
  16 Featherweight
  16 Flyweight
  16 Heavyweight
  16 Light Heavyweight
  16 Lightweight
  16 Middleweight
  16 Welterweight
  16 Women's Bantamweight
  16 Women's Flyweight
  16 Women's Strawweight
```

---

## Phase 3: Fight Matrix Historical Data ⏳ NOT STARTED

**Goal:** Scrape Fight Matrix historical rankings to compute peak rankings

### Deliverables

1. **Fight Matrix Parser**
   - File: `scraper/utils/fightmatrix_rankings_parser.py` (to create)
   - Function: `parse_fightmatrix_rankings_page(html, rank_date)`
   - Purpose: Extract rankings from Fight Matrix HTML
   - Research needed: Inspect Fight Matrix HTML structure first

2. **Fight Matrix Spider**
   - File: `scraper/spiders/fightmatrix_rankings.py` (to create)
   - Name: `fightmatrix_rankings`
   - Strategy: Iterate over last 12 months of ranking snapshots
   - URL pattern: Determine from Fight Matrix website structure

3. **Import Historical Data**
   - Script: `scripts/import_fightmatrix_rankings.py` (to create)
   - Use `FighterNameMatcher` to match names → fighter IDs
   - Use `RankingRepository.upsert_ranking()` to insert
   - Handle date ranges (last 12 months)

4. **Peak Ranking Computation**
   - Script: `scripts/compute_peak_rankings.py` (to create)
   - Query: `SELECT fighter_id, MIN(rank) FROM fighter_rankings GROUP BY fighter_id`
   - Store: Either in `fighters` table or compute on-the-fly in API

### Implementation Notes
- Fight Matrix may have different division naming → normalize
- May need to handle weekly vs monthly snapshots
- Consider rate limiting (delay between requests)
- Validate data quality before bulk import

---

## Phase 4: Backend API ⏳ NOT STARTED

**Goal:** Expose rankings data via REST API

### Deliverables

1. **Rankings Service**
   - File: `backend/services/ranking_service.py` (to create)
   - Class: `RankingService`
   - Methods:
     - `get_current_rankings(division, source)` - Current rankings
     - `get_fighter_ranking_history(fighter_id)` - Historical trend
     - `get_peak_ranking(fighter_id)` - Best rank achieved
     - `get_division_rankings(division)` - Full division leaderboard

2. **Pydantic Response Schemas**
   - File: `backend/schemas/ranking.py` (to create)
   - Models:
     - `RankingResponse` - Single ranking snapshot
     - `CurrentRankingsResponse` - Division leaderboard
     - `RankingHistoryResponse` - Time series data
     - `PeakRankingResponse` - Peak achievement

3. **API Endpoints**
   - File: `backend/api/rankings.py` (to create)
   - Routes:
     - `GET /rankings/` - List all current rankings
     - `GET /rankings/{division}` - Division-specific rankings
     - `GET /rankings/fighter/{fighter_id}` - Fighter's ranking history
     - `GET /rankings/fighter/{fighter_id}/peak` - Fighter's peak ranking
   - Query params: `?source=ufc`, `?date=2025-11-09`, `?limit=10`

4. **Update Fighter Endpoints**
   - File: `backend/api/fighters.py`
   - Modify `GET /fighters/{id}` to include current rank + peak rank
   - Modify `GET /fighters/` to support `?ranked_only=true` filter
   - Add rank-based sorting: `?sort=current_rank` or `?sort=peak_rank`

5. **API Tests**
   - File: `tests/api/test_rankings.py` (to create)
   - Test all endpoints with mock data
   - Test edge cases: NR fighters, interim champions, division mismatches

### API Design Example
```json
GET /rankings/Lightweight
{
  "division": "Lightweight",
  "source": "ufc",
  "rank_date": "2025-11-09",
  "rankings": [
    {
      "rank": 0,
      "fighter_id": "abc123",
      "fighter_name": "Ilia Topuria",
      "is_interim": false,
      "previous_rank": 0,
      "movement": "same"
    },
    {
      "rank": 1,
      "fighter_id": "def456",
      "fighter_name": "Islam Makhachev",
      "is_interim": false,
      "previous_rank": 2,
      "movement": "up"
    }
  ]
}
```

---

## Phase 5: Frontend UI ⏳ NOT STARTED

**Goal:** Display rankings in UFC Pokedex interface

### Deliverables

1. **TypeScript Types**
   - Run: `make types-generate` to regenerate from OpenAPI
   - File: `frontend/src/lib/generated/api-schema.ts` (auto-generated)
   - Ensures type safety for new ranking endpoints

2. **RankingBadge Component**
   - File: `frontend/src/components/rankings/RankingBadge.tsx` (to create)
   - Props: `rank`, `isChampion`, `isInterim`, `peakRank`
   - Displays: "#1" or "C" or "NR (Peak: #3)"
   - Styling: Champion gold, top 5 silver, top 10 bronze, NR gray

3. **DivisionRankings Component**
   - File: `frontend/src/components/rankings/DivisionRankings.tsx` (to create)
   - Props: `division`
   - Fetches: `GET /rankings/{division}`
   - Displays: Leaderboard table with rank, fighter name, movement indicators

4. **RankingHistory Component**
   - File: `frontend/src/components/rankings/RankingHistory.tsx` (to create)
   - Props: `fighterId`
   - Fetches: `GET /rankings/fighter/{id}`
   - Uses: Recharts LineChart to show rank over time
   - Y-axis: Inverted (rank 1 at top, rank 15 at bottom)

5. **PeakRankingCard Component**
   - File: `frontend/src/components/rankings/PeakRankingCard.tsx` (to create)
   - Props: `fighterId`, `peakRank`, `peakDate`
   - Displays: "Career High: #3 (Sep 2024)" with visual highlight

6. **Update EnhancedFighterCard**
   - File: `frontend/src/components/fighter/EnhancedFighterCard.tsx`
   - Add: RankingBadge to corner of card
   - Show: Current rank + peak rank on hover

7. **Update FighterDetail Page**
   - File: `frontend/app/fighters/[id]/page.tsx`
   - Add: RankingHistory chart section
   - Add: PeakRankingCard in sidebar
   - Add: Division context (e.g., "#3 of 16 in Lightweight")

8. **Create Rankings Page**
   - File: `frontend/app/rankings/page.tsx` (to create)
   - Layout: Tabs for each division
   - Content: DivisionRankings component per tab
   - Filters: Currently ranked only, Top 5/10/15 tiers
   - Navigation: Link from main nav

9. **Update useFighters Hook**
   - File: `frontend/src/hooks/useFighters.ts`
   - Add filters: `rankedOnly`, `rankTier`, `division`
   - Add sorting: `sortByRank`, `sortByPeakRank`
   - Integrate with API query params

### UI/UX Notes
- Use Tailwind badge variants for rank styling
- Movement indicators: ↑ green, ↓ red, − gray
- Loading states for async data fetching
- Empty states for NR fighters with no history
- Responsive design for mobile rankings tables

---

## Phase 6: Testing & Polish ⏳ NOT STARTED

**Goal:** E2E testing, edge case handling, documentation

### Deliverables

1. **Playwright E2E Tests**
   - File: `tests/e2e/rankings.spec.ts` (to create)
   - Test scenarios:
     - View division rankings page
     - Click fighter to see ranking history
     - Filter by rank tier
     - Sort by current/peak rank
     - Navigate between divisions

2. **Name Matching Edge Cases**
   - Review unmatched fighters in logs
   - Add manual mappings for known mismatches
   - Consider adding nickname matching
   - Document ambiguous cases

3. **UI Polish**
   - Add animations: Rank change transitions, chart tooltips
   - Loading states: Skeleton screens for rankings tables
   - Error states: Graceful failures for missing data
   - Accessibility: ARIA labels, keyboard navigation

4. **Documentation**
   - Update: `CLAUDE.md` with rankings feature details
   - Document: Scraper usage (`make scrape-rankings`)
   - Document: Data import process
   - Document: API endpoints in OpenAPI spec

---

## Code Review Fixes Applied ✅

All code review issues have been addressed (2 review passes):

### First Review Pass
1. **✅ UNIQUE constraint added to initial migration**
   - Migration: `f143b7233ba8_add_fighter_rankings_table.py`
   - Constraint: `uq_fighter_rankings_natural_key` on (fighter_id, division, rank_date, source)
   - DB now enforces natural key uniqueness (prevents duplicate snapshots)

2. **✅ FighterRanking.id auto-generation**
   - Added: `import uuid` to `backend/db/models/__init__.py`
   - Added: `default=lambda: str(uuid.uuid4())`
   - No longer requires manual ID generation

3. **✅ Name matcher duplicate handling**
   - Changed: Dict → List of tuples `[(name, fighter)]`
   - All fighters with duplicate names preserved for matching
   - Processor function extracts name from tuple for rapidfuzz

4. **✅ Division mismatch threshold check**
   - Added: Re-check threshold after 0.9x penalty
   - Rejects match if adjusted confidence < min_confidence
   - Prevents same-name-different-division mismatches

5. **✅ Record tiebreaker removed**
   - Removed: False 70-79% "tiebreaker" logic
   - Removed: `_boost_confidence_with_record()` method
   - Now honest: Matches <80% are rejected (manual review required)
   - Rankings don't include records, so no validation possible

6. **✅ Division name normalization**
   - Applied: `normalize_division_name()` in UFC parser
   - Ensures consistent DB storage and lookups

### Second Review Pass (Critical Fixes)
1. **✅ UNIQUE constraint in initial migration** (moved from separate migration)
   - Deleted: Redundant `0ff38dee59d4_add_unique_constraint_fighter_rankings.py`
   - Added: Constraint directly to `f143b7233ba8_add_fighter_rankings_table.py`
   - Prevents concurrent scrapes from inserting duplicates

2. **✅ uuid import added**
   - File: `backend/db/models/__init__.py:3`
   - Prevents NameError when inserting first ranking

3. **✅ False record tiebreaker removed**
   - Removed: Misleading 70-79% confidence boost logic
   - Removed: Unused `_boost_confidence_with_record()` method
   - Clear communication: No record validation available

---

## Key Files Reference

### Backend
- `backend/db/models/__init__.py:188-230` - FighterRanking model
- `backend/db/repositories/ranking_repository.py` - RankingRepository
- `backend/db/migrations/versions/f143b7233ba8_*.py` - Initial migration
- `backend/db/migrations/versions/0ff38dee59d4_*.py` - UNIQUE constraint

### Scraper
- `scraper/models/fighter.py:103-169` - FighterRankingItem
- `scraper/utils/name_matcher.py` - FighterNameMatcher
- `scraper/utils/ufc_rankings_parser.py` - UFC parser
- `scraper/spiders/ufc_rankings.py` - UFC spider
- `scraper/pipelines/validation.py` - Updated for rankings

### Frontend (To Create)
- `frontend/src/components/rankings/RankingBadge.tsx`
- `frontend/src/components/rankings/DivisionRankings.tsx`
- `frontend/src/components/rankings/RankingHistory.tsx`
- `frontend/app/rankings/page.tsx`

---

## Running the Scraper

### Current UFC Rankings
```bash
# Scrape current UFC rankings
.venv/bin/scrapy crawl ufc_rankings -o data/processed/ufc_rankings.json

# Import to database (after implementing import script)
.venv/bin/python scripts/import_ufc_rankings.py
```

### Future: Historical Rankings
```bash
# Scrape Fight Matrix historical data
.venv/bin/scrapy crawl fightmatrix_rankings -a months=12

# Compute peak rankings
.venv/bin/python scripts/compute_peak_rankings.py
```

---

## Known Limitations & Future Enhancements

### Current Limitations
1. **No record-based matching** - Name matcher lacks record validation
2. **UFC.com only** - Fight Matrix scraper not implemented
3. **No historical data** - Peak rankings require Fight Matrix integration
4. **Manual import** - No automated scraping schedule

### Future Enhancements
1. **Scheduled scraping** - Weekly cron job to update rankings
2. **Ranking notifications** - Alert on fighter rank changes
3. **Pound-for-pound rankings** - Currently skipped, could add
4. **Movement indicators** - Track week-over-week changes
5. **Record validation** - Implement actual record comparison if data available
6. **Multi-source aggregation** - Combine UFC + Fight Matrix + Tapology

---

## Handoff Checklist for Next Engineer

### Before Starting
- [ ] Read entire plan document
- [ ] Review Phase 1-2 completed code
- [ ] Understand rank storage convention (0=Champion, 1-15=Ranked, NULL=NR)
- [ ] Run UFC rankings spider to verify it works
- [ ] Apply database migrations (`make db-upgrade`)

### Phase 3 Start
- [ ] Research Fight Matrix website structure
- [ ] Inspect HTML to determine correct selectors
- [ ] Create parser based on UFC parser pattern
- [ ] Test parser with sample HTML
- [ ] Implement spider with 12-month date range
- [ ] Run import script and verify data quality

### Questions to Resolve
1. Fight Matrix URL pattern for historical rankings?
2. How far back should we scrape (12 months sufficient)?
3. Store peak rankings in DB or compute on-the-fly?
4. Should we scrape Tapology as a third source?

### Success Criteria
- All rankings importable without name matching failures
- Peak rankings accurate for top fighters
- API endpoints respond < 200ms
- UI components match design mockups
- E2E tests pass on CI

---

**Last Updated:** 2025-11-09 20:40 PM
**Next Phase:** Phase 3 - Fight Matrix Historical Data
**Blockers:** None
**Questions:** See "Questions to Resolve" section above
