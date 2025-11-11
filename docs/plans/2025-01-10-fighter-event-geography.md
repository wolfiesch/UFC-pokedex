# Fighter & Event Geography Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add geographical information (birthplace, nationality, "fighting out of") to fighters and events, with country flag UI components.

**Architecture:** Four-phase approach: (1) Extend database schema with location fields, (2) Update scrapers to extract location data from UFCStats and Sherdog, (3) Backfill existing data, (4) Add frontend UI with country flags using `country-flag-icons` library.

**Tech Stack:** PostgreSQL (new columns), Alembic (migration), Scrapy (data extraction), country-flag-icons (React flag components), ISO 3166-1 alpha-2 country codes.

---

## Phase 1: Database Schema Updates

### Task 1: Add Location Fields to Fighter Model

**Files:**
- Modify: `backend/db/models/__init__.py` (Fighter class around line 15)
- Create: `backend/db/migrations/versions/YYYYMMDD_add_fighter_geography.py`

**Step 1: Add geography fields to Fighter model**

In `backend/db/models/__init__.py`, add these fields to the `Fighter` class after the `dob` field:

```python
# Geography fields
birthplace = Column(String, nullable=True, index=True)  # e.g., "Sacramento, California, USA"
nationality = Column(String, nullable=True, index=True)  # ISO country code: "US", "BR", "IE"
fighting_out_of = Column(String, nullable=True, index=True)  # e.g., "Las Vegas, Nevada, USA"
```

**Step 2: Create Alembic migration**

Run: `make db-upgrade` will fail because schema changed. First create migration:

```bash
.venv/bin/python -m alembic revision -m "add_fighter_geography_fields"
```

Expected: Creates file like `backend/db/migrations/versions/abc123_add_fighter_geography_fields.py`

**Step 3: Implement migration upgrade()**

Edit the generated migration file:

```python
def upgrade() -> None:
    op.add_column('fighters', sa.Column('birthplace', sa.String(), nullable=True))
    op.add_column('fighters', sa.Column('nationality', sa.String(), nullable=True))
    op.add_column('fighters', sa.Column('fighting_out_of', sa.String(), nullable=True))

    # Add indexes for filtering by location
    op.create_index(op.f('ix_fighters_birthplace'), 'fighters', ['birthplace'], unique=False)
    op.create_index(op.f('ix_fighters_nationality'), 'fighters', ['nationality'], unique=False)
    op.create_index(op.f('ix_fighters_fighting_out_of'), 'fighters', ['fighting_out_of'], unique=False)
```

**Step 4: Implement migration downgrade()**

```python
def downgrade() -> None:
    op.drop_index(op.f('ix_fighters_fighting_out_of'), table_name='fighters')
    op.drop_index(op.f('ix_fighters_nationality'), table_name='fighters')
    op.drop_index(op.f('ix_fighters_birthplace'), table_name='fighters')

    op.drop_column('fighters', 'fighting_out_of')
    op.drop_column('fighters', 'nationality')
    op.drop_column('fighters', 'birthplace')
```

**Step 5: Run migration**

Run: `make db-upgrade`
Expected: "Running upgrade ... -> abc123, add_fighter_geography_fields"

**Step 6: Test rollback**

Run: `make db-downgrade`
Expected: Columns removed successfully

Run: `make db-upgrade`
Expected: Columns re-added successfully

**Step 7: Commit**

```bash
git add backend/db/models/__init__.py backend/db/migrations/versions/*_add_fighter_geography_fields.py
git commit -m "feat(db): add geography fields to Fighter model (birthplace, nationality, fighting_out_of)"
```

---

### Task 2: Update Event Model (Verify Location Field)

**Files:**
- Read: `backend/db/models/__init__.py` (Event class)

**Step 1: Verify Event.location exists**

Check `Event` model in `backend/db/models/__init__.py` around line 120.

Expected: `location = Column(String, nullable=True)` already exists

**Step 2: Check if location needs index**

If no index exists on `location`, add:

```python
location = Column(String, nullable=True, index=True)
```

**Step 3: Create migration if index was added**

Only if you modified the Event model:

```bash
.venv/bin/python -m alembic revision -m "add_event_location_index"
```

Implement upgrade():
```python
def upgrade() -> None:
    op.create_index(op.f('ix_events_location'), 'events', ['location'], unique=False)
```

Implement downgrade():
```python
def downgrade() -> None:
    op.drop_index(op.f('ix_events_location'), table_name='events')
```

Run: `make db-upgrade`

**Step 4: Commit if changes made**

```bash
git add backend/db/models/__init__.py backend/db/migrations/versions/*_add_event_location_index.py
git commit -m "feat(db): add index to Event.location for filtering"
```

---

## Phase 2: Scraper Updates

### Task 3: Update Pydantic Models for Location Data

**Files:**
- Modify: `scraper/models/fighter.py`

**Step 1: Add location fields to FighterDetail model**

In `scraper/models/fighter.py`, find the `FighterDetail` class (around line 30) and add after `dob`:

```python
# Geography fields
birthplace: Optional[str] = None
nationality: Optional[str] = None  # ISO 3166-1 alpha-2 code
fighting_out_of: Optional[str] = None
```

**Step 2: Verify SherdogFighterDetail has nationality**

Check that `SherdogFighterDetail` class already has:
```python
nationality: Optional[str] = None
```

Expected: Already exists (confirmed in exploration)

**Step 3: Commit**

```bash
git add scraper/models/fighter.py
git commit -m "feat(scraper): add geography fields to FighterDetail model"
```

---

### Task 4: Extract Location Data from UFCStats Parser

**Files:**
- Modify: `scraper/utils/parser.py` (parse_fighter_detail_page function around line 80)

**Step 1: Add birthplace extraction to bio_map parsing**

In `parse_fighter_detail_page()`, after the existing bio_map extractions (height, weight, reach, etc.), add:

```python
# Extract geography fields from bio_map
birthplace = bio_map.get("BIRTHPLACE")
fighting_out_of = bio_map.get("TRAINS AT") or bio_map.get("FIGHTING OUT OF")

# Clean up location strings (remove extra whitespace)
if birthplace:
    birthplace = " ".join(birthplace.split())
if fighting_out_of:
    fighting_out_of = " ".join(fighting_out_of.split())
```

**Step 2: Add to FighterDetail constructor**

Find where `FighterDetail` is instantiated (around line 150) and add:

```python
birthplace=birthplace,
fighting_out_of=fighting_out_of,
```

**Step 3: Test with sample fighter**

Run: `.venv/bin/scrapy crawl fighter_detail -a fighter_ids=5c8f20e07b326498 -o /tmp/test_geo.json`

Expected: Output JSON contains `"birthplace": "Sacramento, California, USA"` and `"fighting_out_of": "Sacramento, California, USA"`

**Step 4: Commit**

```bash
git add scraper/utils/parser.py
git commit -m "feat(scraper): extract birthplace and fighting_out_of from UFCStats bio"
```

---

### Task 5: Map Sherdog Nationality to ISO Country Codes

**Files:**
- Create: `scraper/utils/country_mapping.py`
- Modify: `scraper/utils/sherdog_parser.py`

**Step 1: Create country name to ISO code mapping**

Create `scraper/utils/country_mapping.py`:

```python
"""Map country names to ISO 3166-1 alpha-2 codes."""

# Common country name variations to ISO 3166-1 alpha-2 codes
COUNTRY_NAME_TO_ISO = {
    # Major UFC countries
    "United States": "US",
    "USA": "US",
    "Brazil": "BR",
    "Brasil": "BR",
    "Canada": "CA",
    "United Kingdom": "GB",
    "UK": "GB",
    "England": "GB",
    "Ireland": "IE",
    "Russia": "RU",
    "Russian Federation": "RU",
    "Mexico": "MX",
    "Australia": "AU",
    "Poland": "PL",
    "France": "FR",
    "Netherlands": "NL",
    "Sweden": "SE",
    "Germany": "DE",
    "Spain": "ES",
    "Italy": "IT",
    "Japan": "JP",
    "South Korea": "KR",
    "Korea": "KR",
    "China": "CN",
    "New Zealand": "NZ",
    "Argentina": "AR",
    "Chile": "CL",
    "Austria": "AT",
    "Belgium": "BE",
    "Croatia": "HR",
    "Czech Republic": "CZ",
    "Denmark": "DK",
    "Finland": "FI",
    "Georgia": "GE",
    "Greece": "GR",
    "Iceland": "IS",
    "Kazakhstan": "KZ",
    "Lithuania": "LT",
    "Norway": "NO",
    "Portugal": "PT",
    "Romania": "RO",
    "Serbia": "RS",
    "Slovakia": "SK",
    "Slovenia": "SI",
    "Switzerland": "CH",
    "Turkey": "TR",
    "Ukraine": "UA",
    "South Africa": "ZA",
    "Nigeria": "NG",
    "Cameroon": "CM",
    "Egypt": "EG",
    "Morocco": "MA",
    "Tunisia": "TN",
    "Israel": "IL",
    "Philippines": "PH",
    "Thailand": "TH",
    "Indonesia": "ID",
    "Vietnam": "VN",
    "India": "IN",
    "Pakistan": "PK",
    "Afghanistan": "AF",
    "Iraq": "IQ",
    "Iran": "IR",
    "Lebanon": "LB",
    "Syria": "SY",
    "Saudi Arabia": "SA",
    "United Arab Emirates": "AE",
    "UAE": "AE",
}


def normalize_nationality(country_name: str | None) -> str | None:
    """
    Convert country name to ISO 3166-1 alpha-2 code.

    Args:
        country_name: Full country name (e.g., "United States")

    Returns:
        ISO alpha-2 code (e.g., "US") or None if not found
    """
    if not country_name:
        return None

    # Clean and normalize
    country_name = country_name.strip()

    # Try exact match first
    if country_name in COUNTRY_NAME_TO_ISO:
        return COUNTRY_NAME_TO_ISO[country_name]

    # Try case-insensitive match
    for name, code in COUNTRY_NAME_TO_ISO.items():
        if name.lower() == country_name.lower():
            return code

    # Log unmapped countries for future additions
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Unmapped country name: '{country_name}'")

    return None
```

**Step 2: Use mapping in Sherdog parser**

In `scraper/utils/sherdog_parser.py`, add import at top:

```python
from scraper.utils.country_mapping import normalize_nationality
```

Find where nationality is extracted (around line 264-268) and update:

```python
# Extract nationality (convert to ISO code)
nationality_elem = soup.find("span", itemprop="nationality")
nationality_raw = nationality_elem.get_text(strip=True) if nationality_elem else None
nationality = normalize_nationality(nationality_raw)
```

**Step 3: Update SherdogFighterDetail instantiation**

Ensure the `nationality` variable (now ISO code) is passed to the model.

**Step 4: Test with known fighter**

Run: `.venv/bin/python scraper/utils/sherdog_parser.py` (if it has a `__main__` block for testing)

Or test via full scraper with a fighter that has Sherdog data.

Expected: `nationality` field contains "US", "BR", "IE" etc., not full country names.

**Step 5: Commit**

```bash
git add scraper/utils/country_mapping.py scraper/utils/sherdog_parser.py
git commit -m "feat(scraper): map Sherdog nationality to ISO country codes"
```

---

### Task 6: Update Fighter Detail Spider to Store Location Data

**Files:**
- Modify: `scraper/spiders/fighter_detail.py`

**Step 1: Verify spider uses updated models**

Check that `FighterDetailSpider` imports and uses `FighterDetail` from `scraper/models/fighter.py`.

Expected: Already imports correctly.

**Step 2: Test full scraping pipeline**

Run: `.venv/bin/scrapy crawl fighter_detail -a fighter_ids=5c8f20e07b326498 -o /tmp/test_full_geo.json`

Expected: Output JSON contains:
```json
{
  "birthplace": "Sacramento, California, USA",
  "nationality": "US",
  "fighting_out_of": "Sacramento, California, USA"
}
```

**Step 3: Verify validation pipeline passes**

The `ValidationPipeline` should validate the new fields automatically via Pydantic.

Check logs for validation errors.

Expected: No validation errors.

**Step 4: Commit if changes made**

```bash
git add scraper/spiders/fighter_detail.py
git commit -m "feat(scraper): spider now captures geography fields"
```

---

## Phase 3: Backend API Updates

### Task 7: Update API Response Schemas

**Files:**
- Modify: `backend/schemas/fighter.py`

**Step 1: Add geography fields to FighterListItem**

In `backend/schemas/fighter.py`, find `FighterListItem` (around line 10) and add:

```python
# Geography fields
birthplace: str | None = None
nationality: str | None = None  # ISO 3166-1 alpha-2 code
fighting_out_of: str | None = None
```

**Step 2: Add geography fields to FighterDetail**

In the same file, find `FighterDetail` (around line 30) and add:

```python
# Geography fields (same as FighterListItem)
birthplace: str | None = None
nationality: str | None = None
fighting_out_of: str | None = None
```

**Step 3: Update FighterDetail Config example**

Update the `Config` class's `json_schema_extra` example to include:

```python
"birthplace": "Sacramento, California, USA",
"nationality": "US",
"fighting_out_of": "Sacramento, California, USA",
```

**Step 4: Commit**

```bash
git add backend/schemas/fighter.py
git commit -m "feat(api): add geography fields to fighter response schemas"
```

---

### Task 8: Update Repository to Return Location Data

**Files:**
- Modify: `backend/db/repositories/fighter_repository.py`

**Step 1: Add geography fields to list_fighters query**

In `fighter_repository.py`, find the `list_fighters` method (around line 50). The SELECT statement should automatically include the new columns since it's using the ORM model.

Verify the query returns Fighter objects with geography fields populated.

**Step 2: Add geography fields to get_fighter query**

Similarly, `get_fighter` method should automatically return the new fields.

**Step 3: Test via Python shell**

```python
from backend.db.connection import get_session
from backend.db.repositories.fighter_repository import PostgreSQLFighterRepository

async def test():
    async for session in get_session():
        repo = PostgreSQLFighterRepository(session)
        fighters = await repo.list_fighters(limit=1)
        print(fighters[0].nationality)  # Should print ISO code or None

import asyncio
asyncio.run(test())
```

Expected: Prints nationality value (or None if not backfilled yet).

**Step 4: Commit if changes made**

```bash
git add backend/db/repositories/fighter_repository.py
git commit -m "feat(api): repository returns geography fields"
```

---

### Task 9: Add Nationality Filter to API

**Files:**
- Modify: `backend/api/fighters.py`
- Modify: `backend/services/fighter_service.py`
- Modify: `backend/db/repositories/fighter_repository.py`

**Step 1: Add nationality parameter to GET /fighters/ endpoint**

In `backend/api/fighters.py`, update the `list_fighters` route (around line 20):

```python
@router.get("/", response_model=FighterListResponse)
async def list_fighters(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    stance: str | None = Query(None),
    nationality: str | None = Query(None, description="Filter by ISO country code (e.g., US, BR, IE)"),
    service: FighterService = Depends(get_fighter_service),
) -> FighterListResponse:
    """List fighters with optional filters."""
    fighters, total = await service.list_fighters(
        limit=limit,
        offset=offset,
        stance=stance,
        nationality=nationality,
    )
    return FighterListResponse(fighters=fighters, total=total, limit=limit, offset=offset)
```

**Step 2: Update FighterService.list_fighters**

In `backend/services/fighter_service.py`, add `nationality` parameter:

```python
async def list_fighters(
    self,
    limit: int = 50,
    offset: int = 0,
    stance: str | None = None,
    nationality: str | None = None,
) -> tuple[list[Fighter], int]:
    """List fighters with optional filters."""
    return await self.repository.list_fighters(
        limit=limit,
        offset=offset,
        stance=stance,
        nationality=nationality,
    )
```

**Step 3: Update PostgreSQLFighterRepository.list_fighters**

In `backend/db/repositories/fighter_repository.py`, add nationality filter:

```python
async def list_fighters(
    self,
    limit: int = 50,
    offset: int = 0,
    stance: str | None = None,
    nationality: str | None = None,
) -> tuple[list[Fighter], int]:
    """List fighters with optional filters."""
    query = select(Fighter)

    # Apply filters
    if stance:
        query = query.where(Fighter.stance == stance)
    if nationality:
        query = query.where(Fighter.nationality == nationality)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await self.session.scalar(count_query)

    # Apply pagination
    query = query.limit(limit).offset(offset).order_by(Fighter.name)

    result = await self.session.execute(query)
    fighters = list(result.scalars().all())

    return fighters, total or 0
```

**Step 4: Test API endpoint**

Start backend: `make api-dev`

Test: `curl "http://localhost:8000/fighters/?nationality=US&limit=5"`

Expected: Returns only US fighters (or empty array if none backfilled yet).

**Step 5: Commit**

```bash
git add backend/api/fighters.py backend/services/fighter_service.py backend/db/repositories/fighter_repository.py
git commit -m "feat(api): add nationality filter to GET /fighters/"
```

---

## Phase 4: Data Backfill

### Task 10: Create Data Backfill Script

**Files:**
- Create: `scripts/backfill_fighter_geography.py`

**Step 1: Write backfill script**

Create `scripts/backfill_fighter_geography.py`:

```python
"""
Backfill geography data for existing fighters.

Reads scraped data from data/processed/fighters/ and updates database.
"""
import asyncio
import json
import logging
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import get_session
from backend.db.models import Fighter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill_geography():
    """Backfill geography data from scraped JSON files."""
    scraped_dir = Path("data/processed/fighters")

    if not scraped_dir.exists():
        logger.error(f"Scraped data directory not found: {scraped_dir}")
        return

    async for session in get_session():
        updated_count = 0
        skipped_count = 0

        for json_file in scraped_dir.glob("*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)

                fighter_id = json_file.stem

                # Extract geography fields
                birthplace = data.get("birthplace")
                nationality = data.get("nationality")
                fighting_out_of = data.get("fighting_out_of")

                # Skip if no geography data
                if not any([birthplace, nationality, fighting_out_of]):
                    skipped_count += 1
                    continue

                # Update fighter
                stmt = (
                    update(Fighter)
                    .where(Fighter.id == fighter_id)
                    .values(
                        birthplace=birthplace,
                        nationality=nationality,
                        fighting_out_of=fighting_out_of,
                    )
                )

                result = await session.execute(stmt)

                if result.rowcount > 0:
                    updated_count += 1
                    logger.info(
                        f"Updated {fighter_id}: "
                        f"nationality={nationality}, "
                        f"birthplace={birthplace}, "
                        f"fighting_out_of={fighting_out_of}"
                    )
                else:
                    logger.warning(f"Fighter not found in database: {fighter_id}")
                    skipped_count += 1

            except Exception as e:
                logger.error(f"Error processing {json_file}: {e}")
                skipped_count += 1

        await session.commit()

        logger.info(f"Backfill complete: {updated_count} updated, {skipped_count} skipped")


if __name__ == "__main__":
    asyncio.run(backfill_geography())
```

**Step 2: Make script executable**

Run: `chmod +x scripts/backfill_fighter_geography.py`

**Step 3: Test on small dataset first**

First, re-scrape a few fighters with new geography extraction:

```bash
.venv/bin/scrapy crawl fighter_detail -a fighter_ids=5c8f20e07b326498,0eb6e87c632367de -o data/processed/fighters/{id}.json
```

Then run backfill:

```bash
.venv/bin/python scripts/backfill_fighter_geography.py
```

Expected: "Backfill complete: 2 updated, 0 skipped" (or similar).

**Step 4: Verify data in database**

```bash
PGPASSWORD=ufc_pokedex psql -h localhost -U ufc_pokedex -d ufc_pokedex -c "SELECT name, nationality, birthplace FROM fighters WHERE nationality IS NOT NULL LIMIT 5;"
```

Expected: Shows fighters with populated geography fields.

**Step 5: Commit**

```bash
git add scripts/backfill_fighter_geography.py
git commit -m "feat(scripts): add backfill script for fighter geography"
```

---

### Task 11: Re-scrape All Fighters (Optional)

**Note:** This is optional and time-consuming. Only do this if you want complete data.

**Step 1: Run full fighter detail scrape**

```bash
make scraper-details
```

Expected: Re-scrapes all fighters from `data/processed/fighters_list.jsonl`, now with geography fields.

**Step 2: Run backfill script**

```bash
.venv/bin/python scripts/backfill_fighter_geography.py
```

Expected: Updates thousands of fighters with geography data.

**Step 3: Verify coverage**

```bash
PGPASSWORD=ufc_pokedex psql -h localhost -U ufc_pokedex -d ufc_pokedex -c "SELECT COUNT(*) as total, COUNT(nationality) as with_nationality, COUNT(birthplace) as with_birthplace FROM fighters;"
```

Expected: Shows percentage of fighters with geography data.

---

## Phase 5: Frontend Updates

### Task 12: Install Country Flag Icons Library

**Files:**
- Modify: `frontend/package.json`

**Step 1: Install country-flag-icons**

Run: `cd frontend && npm install country-flag-icons --save`

Expected: Package added to `package.json` dependencies.

**Step 2: Verify installation**

Run: `npm list country-flag-icons`

Expected: Shows installed version (e.g., `country-flag-icons@1.5.21`).

**Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat(frontend): add country-flag-icons library"
```

---

### Task 13: Regenerate TypeScript Types

**Files:**
- Auto-generated: `frontend/src/lib/generated/api-schema.ts`

**Step 1: Ensure backend is running**

Run: `make api-dev`

**Step 2: Generate types**

Run: `make types-generate`

Expected: `frontend/src/lib/generated/api-schema.ts` now includes `birthplace`, `nationality`, `fighting_out_of` in fighter schemas.

**Step 3: Verify types**

Check `frontend/src/lib/generated/api-schema.ts` for:

```typescript
export interface FighterListItem {
  // ... other fields
  birthplace?: string | null;
  nationality?: string | null;
  fighting_out_of?: string | null;
}
```

Expected: Fields are present.

**Step 4: No commit needed**

This file is gitignored and auto-generated.

---

### Task 14: Create CountryFlag Component

**Files:**
- Create: `frontend/src/components/CountryFlag.tsx`

**Step 1: Write CountryFlag component**

Create `frontend/src/components/CountryFlag.tsx`:

```typescript
import React from 'react';
import * as flags from 'country-flag-icons/react/3x2';

interface CountryFlagProps {
  /** ISO 3166-1 alpha-2 country code (e.g., "US", "BR", "IE") */
  countryCode: string;
  /** Alt text for accessibility */
  alt?: string;
  /** CSS class name */
  className?: string;
  /** Flag width (default: 24px) */
  width?: number;
  /** Flag height (default: 16px) */
  height?: number;
}

/**
 * Renders a country flag SVG based on ISO 3166-1 alpha-2 country code.
 * Uses country-flag-icons library.
 */
export default function CountryFlag({
  countryCode,
  alt,
  className = '',
  width = 24,
  height = 16,
}: CountryFlagProps) {
  if (!countryCode || countryCode.length !== 2) {
    return null;
  }

  // Convert to uppercase (ISO codes are uppercase)
  const code = countryCode.toUpperCase() as keyof typeof flags;

  // Get flag component
  const FlagComponent = flags[code];

  if (!FlagComponent) {
    console.warn(`Flag not found for country code: ${code}`);
    return null;
  }

  return (
    <FlagComponent
      title={alt || code}
      className={className}
      style={{ width: `${width}px`, height: `${height}px` }}
    />
  );
}
```

**Step 2: Create Storybook story (optional)**

If you have Storybook configured, create `CountryFlag.stories.tsx`.

**Step 3: Test component in isolation**

Create a test page: `frontend/app/test-flags/page.tsx`

```typescript
import CountryFlag from '@/components/CountryFlag';

export default function TestFlagsPage() {
  const countries = ['US', 'BR', 'IE', 'RU', 'GB', 'CA', 'MX', 'AU'];

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Country Flags Test</h1>
      <div className="space-y-2">
        {countries.map((code) => (
          <div key={code} className="flex items-center gap-2">
            <CountryFlag countryCode={code} alt={code} />
            <span>{code}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Step 4: Verify rendering**

Run: `make frontend`

Visit: `http://localhost:3000/test-flags`

Expected: Shows flags for each country code.

**Step 5: Commit**

```bash
git add frontend/src/components/CountryFlag.tsx frontend/app/test-flags/page.tsx
git commit -m "feat(frontend): add CountryFlag component"
```

---

### Task 15: Add Geography to Fighter Cards

**Files:**
- Modify: `frontend/src/components/fighter/EnhancedFighterCard.tsx`

**Step 1: Import CountryFlag**

At the top of `EnhancedFighterCard.tsx`, add:

```typescript
import CountryFlag from '@/components/CountryFlag';
```

**Step 2: Add nationality badge**

Find the badge section (around line 50, after stance badge) and add:

```typescript
{fighter.nationality && (
  <div className="flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-blue-900/30 text-blue-300 border border-blue-700/30">
    <CountryFlag countryCode={fighter.nationality} width={16} height={12} />
    <span>{fighter.nationality}</span>
  </div>
)}
```

**Step 3: Add "Fighting Out Of" section**

Find the stats section (below record) and add:

```typescript
{fighter.fighting_out_of && (
  <div className="pt-3 border-t border-gray-700">
    <div className="text-xs text-gray-400 mb-1">Fighting Out Of</div>
    <div className="text-sm text-white flex items-center gap-2">
      {fighter.nationality && (
        <CountryFlag countryCode={fighter.nationality} width={20} height={14} />
      )}
      {fighter.fighting_out_of}
    </div>
  </div>
)}
```

**Step 4: Test with dev server**

Run: `make dev-local`

Visit: `http://localhost:3000`

Expected: Fighter cards show nationality flag badge and "Fighting Out Of" location.

**Step 5: Commit**

```bash
git add frontend/src/components/fighter/EnhancedFighterCard.tsx
git commit -m "feat(frontend): display nationality and fighting location on fighter cards"
```

---

### Task 16: Add Nationality Filter to Fighter List

**Files:**
- Modify: `frontend/src/hooks/useFighters.ts`
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/src/store/favoritesStore.ts`

**Step 1: Add nationalityFilter to Zustand store**

In `frontend/src/store/favoritesStore.ts`, add to state:

```typescript
interface FavoritesState {
  favorites: string[];
  searchTerm: string;
  stanceFilter: string | null;
  nationalityFilter: string | null; // NEW
  addFavorite: (fighterId: string) => void;
  removeFavorite: (fighterId: string) => void;
  setSearchTerm: (term: string) => void;
  setStanceFilter: (stance: string | null) => void;
  setNationalityFilter: (nationality: string | null) => void; // NEW
}
```

Add action:

```typescript
setNationalityFilter: (nationality) => set({ nationalityFilter: nationality }),
```

Add to initial state:

```typescript
nationalityFilter: null,
```

**Step 2: Update useFighters hook to use nationality filter**

In `frontend/src/hooks/useFighters.ts`, add nationality to query params:

```typescript
export function useFighters() {
  const { searchTerm, stanceFilter, nationalityFilter } = useFavoritesStore();

  // Build query params
  const params = new URLSearchParams({
    limit: '100',
    offset: '0',
  });

  if (stanceFilter) {
    params.append('stance', stanceFilter);
  }

  if (nationalityFilter) {
    params.append('nationality', nationalityFilter);
  }

  // ... rest of hook
}
```

**Step 3: Add nationality dropdown to home page**

In `frontend/app/page.tsx`, add nationality filter UI:

```typescript
import { useFavoritesStore } from '@/store/favoritesStore';

export default function Home() {
  const { nationalityFilter, setNationalityFilter } = useFavoritesStore();

  // Common UFC nationalities
  const nationalities = [
    { code: 'US', label: 'United States' },
    { code: 'BR', label: 'Brazil' },
    { code: 'IE', label: 'Ireland' },
    { code: 'RU', label: 'Russia' },
    { code: 'CA', label: 'Canada' },
    { code: 'GB', label: 'United Kingdom' },
    { code: 'MX', label: 'Mexico' },
    { code: 'AU', label: 'Australia' },
  ];

  return (
    <main>
      {/* Add after stance filter */}
      <div className="mb-6">
        <label className="block text-sm font-medium mb-2">Nationality</label>
        <select
          value={nationalityFilter || ''}
          onChange={(e) => setNationalityFilter(e.target.value || null)}
          className="w-full md:w-64 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg"
        >
          <option value="">All Nationalities</option>
          {nationalities.map(({ code, label }) => (
            <option key={code} value={code}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {/* Rest of page */}
    </main>
  );
}
```

**Step 4: Test filtering**

Run: `make dev-local`

Visit: `http://localhost:3000`

Select "Brazil" from nationality dropdown.

Expected: Only Brazilian fighters are displayed.

**Step 5: Commit**

```bash
git add frontend/src/hooks/useFighters.ts frontend/app/page.tsx frontend/src/store/favoritesStore.ts
git commit -m "feat(frontend): add nationality filter to fighter list"
```

---

### Task 17: Add Birthplace to Fighter Detail Page

**Files:**
- Modify: `frontend/app/fighters/[id]/page.tsx`

**Step 1: Import CountryFlag**

At the top of the file, add:

```typescript
import CountryFlag from '@/components/CountryFlag';
```

**Step 2: Add birthplace section**

Find the fighter info section (around the bio stats) and add:

```typescript
{fighter.birthplace && (
  <div className="bg-gray-800 rounded-lg p-4">
    <h3 className="text-sm font-medium text-gray-400 mb-2">Birthplace</h3>
    <div className="flex items-center gap-2">
      {fighter.nationality && (
        <CountryFlag countryCode={fighter.nationality} width={24} height={16} />
      )}
      <p className="text-white">{fighter.birthplace}</p>
    </div>
  </div>
)}

{fighter.fighting_out_of && (
  <div className="bg-gray-800 rounded-lg p-4">
    <h3 className="text-sm font-medium text-gray-400 mb-2">Fighting Out Of</h3>
    <div className="flex items-center gap-2">
      {fighter.nationality && (
        <CountryFlag countryCode={fighter.nationality} width={24} height={16} />
      )}
      <p className="text-white">{fighter.fighting_out_of}</p>
    </div>
  </div>
)}
```

**Step 3: Test detail page**

Visit: `http://localhost:3000/fighters/{fighter_id}` (pick a fighter with geography data)

Expected: Shows birthplace and fighting location with flags.

**Step 4: Commit**

```bash
git add frontend/app/fighters/[id]/page.tsx
git commit -m "feat(frontend): display birthplace and fighting location on detail page"
```

---

## Phase 6: Event Geography (Future Enhancement)

**Note:** Event location already exists in database. No changes needed unless you want to add country flags to events.

### Task 18: Add Event Location Display (Optional)

**Files:**
- Modify: `frontend/app/events/page.tsx` (if exists)
- Modify: Event detail components

**Step 1: Parse event location for country**

Create helper function to extract country from location string:

```typescript
function extractCountryFromLocation(location: string): string | null {
  // Most events are formatted: "City, State/Province, COUNTRY"
  const parts = location.split(',').map(s => s.trim());

  if (parts.length >= 3) {
    // Last part is likely country
    const country = parts[parts.length - 1];

    // Map common event countries
    const countryMap: Record<string, string> = {
      'USA': 'US',
      'United States': 'US',
      'Brazil': 'BR',
      'UK': 'GB',
      'United Kingdom': 'GB',
      'Canada': 'CA',
      'Australia': 'AU',
      // Add more as needed
    };

    return countryMap[country] || null;
  }

  return null;
}
```

**Step 2: Display flag on event cards**

Use `CountryFlag` component with parsed country code.

**Step 3: Test and commit**

---

## Testing & Validation Checklist

After completing all tasks, verify:

- [ ] Database migration runs without errors (upgrade + downgrade)
- [ ] Scraper extracts birthplace, nationality, fighting_out_of from UFCStats
- [ ] Scraper extracts nationality from Sherdog and converts to ISO codes
- [ ] Scraped data includes geography fields in JSON output
- [ ] Backfill script successfully updates existing fighters
- [ ] API returns geography fields in GET /fighters/ response
- [ ] API nationality filter works correctly
- [ ] Frontend displays country flags on fighter cards
- [ ] Frontend nationality filter updates fighter list
- [ ] Fighter detail page shows birthplace and fighting location
- [ ] TypeScript types are regenerated and include geography fields
- [ ] No TypeScript compilation errors
- [ ] Country flags render for all supported ISO codes

---

## Rollback Plan

If issues arise, rollback in reverse order:

1. **Frontend:** `git revert` commits for frontend components
2. **API:** `git revert` commits for API changes
3. **Scraper:** `git revert` commits for scraper changes
4. **Database:** Run `make db-downgrade` to remove geography columns

---

## Future Enhancements

- Add city/region filtering (extract from birthplace/fighting_out_of)
- Add map visualization of fighter origins
- Add "born on this day" feature using birthplace + DOB
- Add nationality statistics/charts
- Support multiple nationalities (dual citizenship)
- Add event location country flags
- Add geographical heatmap for event locations

---

**Plan created:** 2025-01-10

**Estimated implementation time:** 6-8 hours

**Dependencies:** PostgreSQL, Alembic, Scrapy, country-flag-icons

**Related Documentation:**
- @superpowers:executing-plans (for batch execution)
- @superpowers:subagent-driven-development (for incremental execution)
- @superpowers:test-driven-development (for test-first approach)
- @superpowers:verification-before-completion (for final validation)
