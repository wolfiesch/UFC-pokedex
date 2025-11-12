# UFC-Pokedex Data Structure Analysis: Location & Geography Fields

## Executive Summary

**Current Status:** No geographic location fields exist in the main UFC Fighter data pipeline.

**Available Location Data Sources:**
1. **Events Table** - Has `location` field (event venues)
2. **Sherdog Integration** - Provides `nationality` field (fighter's country)
3. **UFCStats.com** - Limited location data in biography section

---

## 1. Current Database Schema

### Fighter Model (`backend/db/models/__init__.py`)

**Current Fighter Fields:**
```python
class Fighter(Base):
    id: str                              # Primary key
    name: str
    nickname: str | None
    division: str | None
    height: str | None
    weight: str | None
    reach: str | None
    leg_reach: str | None
    stance: str | None                  # Index for filtering
    dob: date | None
    record: str | None
    sherdog_id: int | None             # Link to Sherdog data
    image_url: str | None
    image_scraped_at: datetime | None
    cropped_image_url: str | None
    face_detection_confidence: float | None
    crop_processed_at: datetime | None
    is_current_champion: bool
    is_former_champion: bool
    was_interim: bool
    championship_history: dict[str, Any] | None  # JSON field
    current_streak_type: str | None
    current_streak_count: int
    last_fight_date: date | None
```

**MISSING LOCATION FIELDS:**
- ❌ `birthplace` / `hometown` - Fighter's place of birth
- ❌ `fighting_out_of` / `based_in` - Where fighter currently trains/resides
- ❌ `nationality` / `country` - Fighter's country of origin

### Event Model (`backend/db/models/__init__.py`)

**Current Event Fields:**
```python
class Event(Base):
    id: str
    name: str
    date: date                          # Indexed
    location: str | None                # ← EVENT LOCATION EXISTS
    status: str                         # 'upcoming' or 'completed'
    venue: str | None
    broadcast: str | None
    promotion: str                      # Default "UFC"
    ufcstats_url: str | None
    tapology_url: str | None
    sherdog_url: str | None
```

**Note:** Events have location data, but fighters don't.

---

## 2. Scraper Data Models

### Fighter Scraper Models (`scraper/models/fighter.py`)

**FighterListItem:**
```python
class FighterListItem(BaseModel):
    fighter_id: str
    detail_url: HttpUrl
    name: str
    nickname: str | None = None
    height: str | None = None
    weight: str | None = None
    division: str | None = None
    reach: str | None = None
    stance: str | None = None
    dob: date | None = None
    # ❌ NO LOCATION FIELDS
```

**FighterDetail:**
```python
class FighterDetail(FighterListItem):
    record: str | None = None
    leg_reach: str | None = None
    age: int | None = None
    striking: dict[str, Any] = Field(default_factory=dict)
    grappling: dict[str, Any] = Field(default_factory=dict)
    significant_strikes: dict[str, Any] = Field(default_factory=dict)
    takedown_stats: dict[str, Any] = Field(default_factory=dict)
    fight_history: list[FightHistoryEntry] = Field(default_factory=list)
    # ❌ NO LOCATION FIELDS
```

**SherdogFighterDetail:** (Exists - has nationality!)
```python
class SherdogFighterDetail(BaseModel):
    # ... basic fields ...
    nationality: str | None = Field(
        None, 
        description="Fighter nationality"
    )
    # ✅ HAS nationality field from Sherdog scraper
    # ❌ NO birthplace/hometown/fighting_out_of
```

---

## 3. What UFCStats.com Provides

### Parser: `scraper/utils/parser.py`

**Biography Section Extraction (`parse_fighter_detail_page`):**
```python
bio_map: dict[str, str | None] = {}
for row in selector.css("ul.b-list__box-list li"):
    label = clean_text(row.css("i::text").get())
    value = next((clean_text(candidate) for candidate in value_candidates), None)
    bio_map[label.upper()] = value
```

**Currently Extracted Bio Fields:**
- `HEIGHT` ✅
- `WEIGHT` ✅
- `REACH` ✅
- `LEG REACH` ✅
- `STANCE` ✅
- `DOB` (Age) ✅
- **BIRTHPLACE** ❓ (Possibly available but not extracted)
- **FIGHTING OUT OF** ❓ (Possibly available but not extracted)

**Data Flow in Parser:**
```
HTML bio_map → FighterDetail model → Database
```

The parser only extracts fields explicitly mapped from the HTML:
- Lines 429-436 show extraction of HEIGHT, WEIGHT, REACH, LEG REACH, STANCE, AGE, DOB
- **No birthplace, hometown, or location data is extracted**

---

## 4. What Sherdog.com Provides

### Sherdog Parser: `scraper/utils/sherdog_parser.py`

**Extracted Fields:**
```python
def parse_sherdog_fighter_detail(response):
    # Extracts:
    - dob_raw: str | None        # "Sep 20, 1989"
    - dob: str | None            # ISO format "1989-09-20"
    - height: str | None         # "6'0\""
    - height_cm: float | None
    - weight: str | None         # "155 lbs"
    - weight_kg: float | None
    - nationality: str | None    # ✅ AVAILABLE! "United States"
    - reach: str | None
    - reach_cm: float | None
    - stance: str | None
```

**Sherdog HTML Structure:**
```html
<strong itemprop="nationality">United States</strong>
<span itemprop="birthDate">Sep 20, 1989</span>
<b itemprop="height">6'0"</b>
<b itemprop="weight">155 lbs</b>
```

**Key Finding:**
- ✅ Sherdog provides `nationality` (extracted in lines 264-268)
- ✅ Sherdog model (`SherdogFighterDetail`) has nationality field
- ❌ Sherdog doesn't provide birthplace or fighting location
- ❌ Nationality from Sherdog is NOT currently stored in Fighter model

---

## 5. Sample Data

### Sample Fighter JSON (`data/processed/fighters/15df64c02b6b0fde.json`)
```json
{
  "fighter_id": "15df64c02b6b0fde",
  "detail_url": "http://ufcstats.com/fighter-details/15df64c02b6b0fde",
  "name": "Danny Abbadi",
  "nickname": "The Assassin",
  "height": "5' 11\"",
  "weight": "155 lbs.",
  "division": "Lightweight",
  "reach": null,
  "stance": "Orthodox",
  "dob": "1983-07-03",
  "record": "4-6-0",
  "leg_reach": null,
  "age": null,
  "striking": { ... },
  "grappling": { ... },
  "significant_strikes": { ... },
  "takedown_stats": { ... },
  "fight_history": [ ... ],
  "item_type": "fighter_detail"
}
```

**Observations:**
- No location fields present
- No nationality field
- Sparse biographical data

---

## 6. API Response Schema (`backend/schemas/fighter.py`)

**FighterListItem Response:**
```python
class FighterListItem(BaseModel):
    fighter_id: str
    detail_url: HttpUrl
    name: str
    nickname: str | None = None
    record: str | None = None
    division: str | None = None
    height: str | None = None
    weight: str | None = None
    reach: str | None = None
    stance: str | None = None
    dob: date | None = None
    image_url: str | None = None
    age: int | None = None
    is_current_champion: bool = False
    is_former_champion: bool = False
    was_interim: bool = False
    current_streak_type: Literal["win", "loss", "draw", "none"] = "none"
    current_streak_count: int = 0
    # Ranking fields...
```

**FighterDetail Response:**
```python
class FighterDetail(FighterListItem):
    leg_reach: str | None = None
    striking: dict[str, Any] = Field(default_factory=dict)
    grappling: dict[str, Any] = Field(default_factory=dict)
    significant_strikes: dict[str, Any] = Field(default_factory=dict)
    takedown_stats: dict[str, Any] = Field(default_factory=dict)
    career: dict[str, Any] = Field(default_factory=dict)
    fight_history: list[FightHistoryEntry] = Field(default_factory=list)
    championship_history: dict[str, Any] = Field(default_factory=dict)
```

**No location fields exposed to frontend**

---

## 7. Event Location Data

**Events List Row Parser (`parse_events_list_row`):**
```python
# Location (column 2)
location = clean_text(row.css("td:nth-child(2)::text").get())
```

**Event Detail Parser (`parse_event_detail_page`):**
```python
# Event metadata from list items
metadata_map: dict[str, str | None] = {}
# Extracts LOCATION field:
location = metadata_map.get("LOCATION")
```

**Event Model Has Location:**
```python
class Event(Base):
    location: str | None    # ← Present for events
```

**Example:** Event location would be "Las Vegas, Nevada" or "New York, New York"

---

## 8. Summary of Available Location Data

| Data Type | Source | Current Storage | Available |
|-----------|--------|-----------------|-----------|
| **Birthplace** | UFCStats HTML (possibly in bio) | ❌ Not extracted | ❓ Need to verify |
| **Fighting Out Of** | UFCStats HTML (possibly in bio) | ❌ Not extracted | ❓ Need to verify |
| **Nationality** | Sherdog (`itemprop="nationality"`) | ❌ Not in Fighter model | ✅ Available in Sherdog scraper |
| **Event Location** | UFCStats events | ✅ Event.location field | ✅ In database |
| **Country Code** | None | ❌ Not available | ❌ Not available |
| **Coordinates (lat/lon)** | None | ❌ Not available | ❌ Not available |

---

## 9. Data Flow Architecture

```
UFCStats.com HTML
    ├─ Biography Section (LIST ITEMS)
    │   ├─ HEIGHT → Extracted ✅
    │   ├─ WEIGHT → Extracted ✅
    │   ├─ REACH → Extracted ✅
    │   ├─ STANCE → Extracted ✅
    │   ├─ DOB → Extracted ✅
    │   ├─ BIRTHPLACE → NOT extracted ❌
    │   └─ FIGHTING OUT OF → NOT extracted ❌
    │
    └─ Fighter Stats
        └─ Strike/Grappling/etc → Extracted ✅

Sherdog.com HTML
    └─ Fighter Bio
        ├─ NATIONALITY → Extracted ✅ (but not stored in Fighter model)
        ├─ DOB → Extracted ✅
        ├─ HEIGHT → Extracted ✅
        ├─ WEIGHT → Extracted ✅
        └─ REACH → Extracted ✅

↓

scraper/models/fighter.py
    ├─ FighterListItem (no location)
    ├─ FighterDetail (no location)
    └─ SherdogFighterDetail (HAS nationality!)

↓

scraper/pipelines/validation.py & storage.py
    └─ Validates and stores to data/processed/fighters/*.json

↓

load_scraped_data script
    └─ Maps to Fighter DB model (missing location fields)

↓

backend/db/models/__init__.py
    └─ Fighter model (NO birthplace, fighting_out_of, nationality)

↓

backend/db/repositories/fighter_repository.py
    └─ Queries database

↓

backend/schemas/fighter.py
    └─ API response (no location fields)

↓

Frontend API calls
    └─ No geographic data available
```

---

## 10. Key Findings

### What We Have
1. ✅ Event locations are captured and stored in database
2. ✅ Sherdog scraper extracts nationality (but not stored)
3. ✅ UFCStats likely has birthplace in biography section

### What We're Missing
1. ❌ No birthplace/hometown field in Fighter model
2. ❌ No nationality field in Fighter model (despite Sherdog data)
3. ❌ No "fighting out of" field in Fighter model
4. ❌ No geocoordinates (latitude/longitude) anywhere
5. ❌ No country code normalization
6. ❌ No location fields exposed in API responses

### Data Extraction Gaps
1. **UFCStats biography section** - Need to verify if BIRTHPLACE and "FIGHTING OUT OF" are available
2. **Sherdog nationality** - Being extracted but not persisted to database
3. **Location standardization** - Even if we extract it, need to normalize format (e.g., "USA" vs "United States")

---

## 11. Recommendations for Adding Geography

### Phase 1: Data Capture
1. Add `birthplace` field to Fighter model (nullable string)
2. Add `nationality` field to Fighter model (nullable string)
3. Add `fighting_out_of` field to Fighter model (nullable string)
4. Create migration to add these columns

### Phase 2: Data Extraction
1. Update `FighterDetail` Pydantic model to include these fields
2. Update `parse_fighter_detail_page()` to extract BIRTHPLACE and FIGHTING OUT OF from bio_map
3. Update `SherdogFighterDetail` model to map nationality properly
4. Update storage pipeline to handle new fields

### Phase 3: Database Population
1. Update `load_scraped_data` script to map new fields from JSON
2. Implement Sherdog nationality import into Fighter records
3. Create backfill script for existing fighters

### Phase 4: API & Frontend
1. Add fields to API response schemas
2. Add fields to frontend components
3. Add filtering/searching by location
4. Consider adding geolocation visualization

---

## File References

| File | Purpose | Location Data |
|------|---------|----------------|
| `backend/db/models/__init__.py` | DB schema | Fighter (none), Event (✓) |
| `scraper/models/fighter.py` | Pydantic models | FighterDetail (none), SherdogFighterDetail (nationality) |
| `scraper/utils/parser.py` | UFCStats parser | Extracts bio_map (missing location fields) |
| `scraper/utils/sherdog_parser.py` | Sherdog parser | Extracts nationality (line 264-268) |
| `scraper/pipelines/validation.py` | Pipeline validation | — |
| `scraper/pipelines/storage.py` | Storage pipeline | — |
| `backend/schemas/fighter.py` | API schema | No location fields |
| `backend/db/repositories/fighter_repository.py` | DB queries | — |
| `data/processed/fighters/*.json` | Sample data | No location fields |

