# Fighter Geographical Data - Design Document

**Date:** 2025-11-11
**Status:** Design Phase
**Author:** Claude Code + User Collaboration

## Table of Contents

1. [Overview](#overview)
2. [Goals & Requirements](#goals--requirements)
3. [Data Sources Analysis](#data-sources-analysis)
4. [Database Schema](#database-schema)
5. [Scraping Architecture](#scraping-architecture)
6. [Fuzzy Matching Strategy](#fuzzy-matching-strategy)
7. [Tiered Enrichment Pipeline](#tiered-enrichment-pipeline)
8. [Data Loading & Migration](#data-loading--migration)
9. [Update & Refresh Strategy](#update--refresh-strategy)
10. [Rate Limiting & Politeness](#rate-limiting--politeness)
11. [API Endpoints](#api-endpoints)
12. [Frontend UI Components](#frontend-ui-components)
13. [Implementation Plan](#implementation-plan)
14. [Open Questions](#open-questions)

---

## Overview

### Problem Statement

The UFC Pokedex currently displays fighter stats (height, weight, reach, record) but lacks geographical context. Users want to know:
- **Where fighters are from** (birthplace)
- **Where fighters train** (gym/city)
- **Ability to filter/explore by location**

### Solution

Implement a three-tiered data enrichment system:
1. **Tier 1**: Scrape UFC.com for birthplace + training gym (~3,000 fighters)
2. **Tier 2**: Use existing Sherdog data for nationality (~1,300 additional fighters)
3. **Tier 3**: Manual curation for historical legends (~50-100 fighters)

### Success Criteria

- ✅ 67%+ fighters have birthplace data (Tier 1)
- ✅ 97%+ fighters have nationality data (Tier 1 + Tier 2)
- ✅ Location data displayed on fighter cards
- ✅ Users can filter fighters by country/gym
- ✅ Automated updates keep data fresh

---

## Goals & Requirements

### Functional Requirements

**FR1: Data Collection**
- Scrape UFC.com for birthplace (city + country)
- Scrape UFC.com for training gym name
- Extract nationality from existing Sherdog data
- Support manual data overrides

**FR2: Data Accuracy**
- Fuzzy match UFC.com fighters to UFCStats database (>90% confidence)
- Handle duplicate fighter names (e.g., "Bruno Silva" x2)
- Flag low-confidence matches for manual review
- Detect and log data changes over time

**FR3: User Experience**
- Display location badges on fighter cards
- Filter fighters by country/city/gym
- Show location statistics (top countries, top gyms)
- Enable search by location ("dublin", "aka", etc.)

**FR4: Data Freshness**
- Daily updates for active fighters
- Weekly updates for recent fighters
- Monthly refresh for all stale data (>90 days)
- Automatic detection of new UFC.com fighters

### Non-Functional Requirements

**NFR1: Performance**
- Location filters use indexed database queries (<100ms)
- Scraping completes within 8-10 hours (initial load)
- Incremental updates complete within 5 minutes

**NFR2: Scalability**
- Support 10,000+ fighters
- Handle 3,000+ UFC.com scrape requests
- Batch processing for large updates

**NFR3: Reliability**
- Respect UFC.com rate limits (2-3 seconds between requests)
- Exponential backoff for errors
- Graceful degradation if sources unavailable

**NFR4: Maintainability**
- Version tracked in git
- Automated tests for matching logic
- Change logs for data updates
- Manual override system

---

## Data Sources Analysis

### UFC.com (Primary Source)

**Coverage:** ~3,106 fighters (current/recent/notable roster)

**Available Data:**
- ✅ **Place of Birth** - Full string (e.g., "Dublin, Ireland")
- ✅ **Trains at** - Gym name (e.g., "SBG Ireland")
- ✅ Age, height, weight, record

**Scraping Strategy:**
1. Scrape `/athletes/all` for fighter slugs
2. Scrape `/athlete/{slug}` for individual profiles
3. Parse `.c-bio__label` and `.c-bio__text` elements

**Infrastructure:**
- Drupal 10 backend
- Varnish/CDN caching (24hr TTL)
- No explicit rate limits
- Pantheon hosting

**Pros:**
- Official, authoritative data
- Consistent HTML structure
- City-level detail for birthplace and training

**Cons:**
- Only includes UFC roster (not all UFCStats fighters)
- No historical fighters (pre-UFC 50 era)
- Requires fuzzy matching to UFCStats IDs

### Sherdog (Secondary Source)

**Coverage:** Most fighters in UFCStats database

**Available Data:**
- ✅ **Nationality** - Country string (e.g., "Irish")
- ✅ Height, weight, DOB (already being scraped)

**Integration:**
- Already integrated in codebase
- Model: `SherdogFighterDetail` (scraper/models/fighter.py:54)
- Just need to add nationality to fighters table

**Pros:**
- Broad coverage (historical + current fighters)
- Already scraping this data
- Free to use

**Cons:**
- Only country-level (no city detail)
- 403 errors on some requests (need to handle)

### UFCStats (Existing Database)

**Coverage:** 4,447 fighters

**Current Data:**
- Fighter name, division, record, stats
- Fight history
- No location data (what we're adding!)

### Manual Curation (Tertiary Source)

**Coverage:** ~50-100 historical legends

**Use Cases:**
- Fighters not on UFC.com (Fedor, Sakuraba, etc.)
- Data corrections/overrides
- Disputed information

**Format:** CSV file with manual entries
```csv
name,ufcstats_id,birthplace,nationality,training_gym
Fedor Emelianenko,abc123,"Rubizhne, Ukraine",Russian,"Red Devil Sport Club"
```

---

## Database Schema

### Fighters Table - New Columns

```sql
-- === BIRTHPLACE (from UFC.com) ===
birthplace_city: VARCHAR(100) NULL
    -- "Dublin", "Lagos", "Las Vegas"
    -- Extracted from birthplace string

birthplace_country: VARCHAR(100) NULL
    -- "Ireland", "Nigeria", "United States"
    -- Extracted from birthplace string

birthplace: VARCHAR(255) NULL
    -- "Dublin, Ireland" (full display string)
    -- Primary field from UFC.com

-- === NATIONALITY (from Sherdog) ===
nationality: VARCHAR(100) NULL
    -- "Irish", "Nigerian", "American"
    -- Note: May differ from birthplace_country
    -- Example: Israel Adesanya - Born Nigeria, Nationality New Zealander

-- === TRAINING LOCATION (from UFC.com) ===
training_gym: VARCHAR(255) NULL
    -- "SBG Ireland", "City Kickboxing", "American Kickboxing Academy"
    -- Free text gym name

training_city: VARCHAR(100) NULL
    -- "Dublin", "Auckland", "San Jose"
    -- Derived via gym location lookup (see Gym Location Normalization)

training_country: VARCHAR(100) NULL
    -- "Ireland", "New Zealand", "United States"
    -- Derived via gym location lookup (see Gym Location Normalization)

-- === DATA SOURCE TRACKING ===
ufc_com_slug: VARCHAR(255) NULL UNIQUE
    -- "conor-mcgregor" (for future updates)
    -- Links to UFC.com athlete page

ufc_com_scraped_at: TIMESTAMP NULL
    -- When we last fetched from UFC.com
    -- Used for refresh scheduling

-- === FUZZY MATCHING METADATA ===
ufc_com_match_confidence: FLOAT NULL
    -- 0-100 fuzzy match score
    -- >90 = auto_high, 70-90 = auto_medium, <70 = manual_review

ufc_com_match_method: VARCHAR(20) NULL
    -- "auto_high" | "auto_medium" | "manual" | "verified"
    -- How this match was created

needs_manual_review: BOOLEAN DEFAULT FALSE
    -- Flag fighters needing human verification
    -- For ambiguous matches or conflicting data
```

### Indexes

```sql
-- Performance optimization for common queries
CREATE INDEX ix_fighters_birthplace_country ON fighters(birthplace_country);
CREATE INDEX ix_fighters_nationality ON fighters(nationality);
CREATE INDEX ix_fighters_training_city ON fighters(training_city);
CREATE INDEX ix_fighters_training_country ON fighters(training_country);
CREATE INDEX ix_fighters_ufc_com_slug ON fighters(ufc_com_slug) UNIQUE;
CREATE INDEX ix_fighters_needs_manual_review ON fighters(needs_manual_review);

-- Composite indexes for common filter combinations
CREATE INDEX ix_fighters_birthplace_country_division ON fighters(birthplace_country, division);
CREATE INDEX ix_fighters_training_country_division ON fighters(training_country, division);
```

### Data Examples

**Example 1: Conor McGregor (all data available)**
```json
{
  "birthplace": "Dublin, Ireland",
  "birthplace_city": "Dublin",
  "birthplace_country": "Ireland",
  "nationality": "Irish",
  "training_gym": "SBG Ireland",
  "training_city": "Dublin",
  "training_country": "Ireland",
  "ufc_com_slug": "conor-mcgregor",
  "ufc_com_match_confidence": 98.5,
  "ufc_com_match_method": "auto_high"
}
```

**Example 2: Israel Adesanya (nationality differs from birthplace)**
```json
{
  "birthplace": "Lagos, Nigeria",
  "birthplace_city": "Lagos",
  "birthplace_country": "Nigeria",
  "nationality": "New Zealander",
  "training_gym": "City Kickboxing",
  "training_city": "Auckland",
  "training_country": "New Zealand",
  "ufc_com_slug": "israel-adesanya",
  "ufc_com_match_confidence": 99.2,
  "ufc_com_match_method": "auto_high"
}
```

**Example 3: Historical fighter (Sherdog only)**
```json
{
  "birthplace": null,
  "birthplace_city": null,
  "birthplace_country": null,
  "nationality": "Russian",
  "training_gym": null,
  "training_city": null,
  "training_country": null,
  "ufc_com_slug": null,
  "ufc_com_match_confidence": null,
  "ufc_com_match_method": null
}
```

---

### Gym Location Normalization

Training gyms on UFC.com rarely include structured city/country data, so `training_city` and `training_country` are populated through a deterministic enrichment step:

1. **Canonical gym lookup:** Maintain `data/manual/gym_locations.csv` with columns `gym_name`, `city`, `country`, `iso2`, `lat`, `lon`. Seed the file with the top ~500 gyms scraped from UFC.com + Sherdog and keep it under version control for transparency.
2. **Automated suggestions:** When a gym is missing from the lookup, run it through `scripts/suggest_gym_location.py`, which queries Photon/OSM (offline cache refreshed weekly) and emits a proposed city/country for manual approval.
3. **Manual overrides:** Curators can pin specific gyms (e.g., multi-site brands like "American Top Team") to a canonical location that best represents the flagship facility.

Only after a gym has a vetted entry do we backfill `training_city`/`training_country`. This guarantees that location filters, stats endpoints, and UI widgets have consistent, reviewable data instead of noisy free text.

---

## Scraping Architecture

### UFC.com Spiders

#### Spider 1: UFC Athletes List

**Name:** `ufc_com_athletes`

**Starting URL:** `https://www.ufc.com/athletes/all`

**Output:** `data/processed/ufc_com_athletes_list.jsonl`

**Fields Extracted:**
```python
{
    "name": str,           # "Conor McGregor"
    "slug": str,           # "conor-mcgregor"
    "division": str,       # "Lightweight"
    "record": str,         # "22-6-0"
    "status": str,         # "Active" | "Retired"
    "profile_url": str     # Full URL
}
```

**Challenges:**
- Pagination: "Load More" button (dynamic loading)
- Total fighters: ~3,106
- May need Selenium/Playwright for infinite scroll

**Solution (decided):**

- Use the Drupal JSON feed that powers the "Load More" widget: `https://www.ufc.com/api/v3/us-en/athletes?offset={offset}&limit=100`.
- Paginate in 100-record batches until `returned_count < 100`.
- Persist raw responses to `data/raw/ufc_com/athletes_{offset}.json` for auditing, then flatten into the `jsonl` output.
- Fallback: if the API ever blocks us, run the same spider with Playwright (`playwright-stealth` profile) to execute the infinite scroll, but this path is only for outages.

#### Spider 2: UFC Athlete Detail

**Name:** `ufc_com_athlete_detail`

**Input:** Slugs from Spider 1

**Output:** `data/processed/ufc_com_fighters/{slug}.json`

**Parsing Logic:**
```python
def parse_athlete_bio(response):
    bio_items = response.css('.c-bio__row')

    data = {}
    for item in bio_items:
        label = item.css('.c-bio__label::text').get()
        value = item.css('.c-bio__text::text').get()

        if label == "Place of Birth":
            # Parse "Dublin, Ireland"
            data["birthplace"] = value.strip()

            # Split into city and country
            if ',' in value:
                city, country = value.split(',', 1)
                data["birthplace_city"] = city.strip()
                data["birthplace_country"] = country.strip()
            else:
                # Handle single value (country only)
                data["birthplace_country"] = value.strip()

        if label == "Trains at":
            data["training_gym"] = value.strip()
            # TODO: Extract city/country from gym name if possible

    return data
```

**Fields Extracted:**
```python
{
    "slug": str,                    # "conor-mcgregor"
    "name": str,                    # "Conor McGregor"
    "birthplace": str | None,       # "Dublin, Ireland"
    "birthplace_city": str | None,  # "Dublin"
    "birthplace_country": str | None, # "Ireland"
    "training_gym": str | None,     # "SBG Ireland"
    "age": int | None,
    "height": str | None,
    "weight": str | None,
    "status": str                   # "Active"
}
```

### Scrapy Settings

```python
# scraper/settings.py - UFC.com specific settings

CUSTOM_SETTINGS = {
    "ufc_com_athlete_detail": {
        # Download delay: 2.5 seconds between requests
        "DOWNLOAD_DELAY": 2.5,

        # Randomize to appear human-like (1.25s - 3.75s)
        "RANDOMIZE_DOWNLOAD_DELAY": True,

        # Only 1 concurrent request to UFC.com
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,

        # AutoThrottle: Adapt to server speed
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 2.0,
        "AUTOTHROTTLE_MAX_DELAY": 60.0,

        # User agent
        "USER_AGENT": "UFC-Pokedex-Bot/1.0 (+https://github.com/user/ufc-pokedex)",

        # Respect robots.txt
        "ROBOTSTXT_OBEY": True,

        # Retry on rate limits
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],

        # HTTP caching (avoid re-scraping)
        "HTTPCACHE_ENABLED": True,
        "HTTPCACHE_EXPIRATION_SECS": 86400,  # 24 hours
    }
}
```

---

## Fuzzy Matching Strategy

### Challenge: Linking UFC.com to UFCStats

**Problem:** UFC.com uses slugs (`conor-mcgregor`), UFCStats uses hex IDs (`f4c49976c75c5ab2`)

**Solution:** Fuzzy name matching with disambiguation signals

### Step 1: Name Normalization

```python
from unidecode import unidecode
import re

def normalize_fighter_name(name: str) -> str:
    """
    Normalize fighter names for matching.

    Examples:
        "José Aldo" → "jose aldo"
        "O'Malley, Sean" → "sean omalley"
        "Jon 'Bones' Jones" → "jon jones"
        "Junior dos Santos" → "junior dos santos"
    """
    # Lowercase
    name = name.lower()

    # Remove accents: José → Jose
    name = unidecode(name)

    # Remove nicknames in quotes/parens
    name = re.sub(r"['\"].*?['\"]", "", name)
    name = re.sub(r"\(.*?\)", "", name)

    # Remove Jr/Sr/II/III
    name = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", name)

    # Remove apostrophes: O'Malley → OMalley
    name = name.replace("'", "")

    # Remove extra whitespace
    name = " ".join(name.split())

    return name.strip()
```

### Step 2: Multi-Algorithm Matching

```python
from rapidfuzz import fuzz

def calculate_match_score(ufcstats_name: str, ufc_com_name: str) -> dict:
    """
    Calculate match confidence using multiple algorithms.
    """
    norm_a = normalize_fighter_name(ufcstats_name)
    norm_b = normalize_fighter_name(ufc_com_name)

    scores = {
        # Token sort: handles word order
        "token_sort": fuzz.token_sort_ratio(norm_a, norm_b),

        # Partial: handles nicknames, extra words
        "partial": fuzz.partial_ratio(norm_a, norm_b),

        # Simple ratio: exact character matching
        "ratio": fuzz.ratio(norm_a, norm_b),

        # Token set: best for ignoring extra tokens
        "token_set": fuzz.token_set_ratio(norm_a, norm_b),
    }

    # Weighted average (token_sort and token_set most reliable)
    final_score = (
        scores["token_sort"] * 0.4 +
        scores["token_set"] * 0.3 +
        scores["partial"] * 0.2 +
        scores["ratio"] * 0.1
    )

    return {
        "scores": scores,
        "confidence": round(final_score, 2),
        "normalized_a": norm_a,
        "normalized_b": norm_b,
    }
```

### Step 3: Duplicate Resolution

**Problem:** Multiple fighters with same name (e.g., "Bruno Silva" x2)

**Solution:** Use disambiguation signals

```python
def calculate_disambiguation_score(
    ufc_com_fighter: dict,
    ufcstats_fighter: dict,
    name_confidence: float
) -> dict:
    """
    Use additional signals beyond name matching.
    """
    bonus_points = 0
    signals = {}

    # Signal 1: Division match (STRONGEST - +15 points)
    if ufc_com_fighter.get("division") and ufcstats_fighter.division:
        division_match = normalize_division(ufc_com_fighter["division"]) == \
                        normalize_division(ufcstats_fighter.division)
        signals["division_match"] = division_match
        if division_match:
            bonus_points += 15

    # Signal 2: Record similarity (MEDIUM - +10 or -20 points)
    if ufc_com_fighter.get("record") and ufcstats_fighter.record:
        record_similarity = compare_records(
            ufc_com_fighter["record"],
            ufcstats_fighter.record
        )
        signals["record_similarity"] = record_similarity
        if record_similarity >= 0.8:
            bonus_points += 10
        elif record_similarity <= 0.3:
            bonus_points -= 20  # Penalty - likely different fighters

    # Signal 3: Age/DOB proximity (MEDIUM - +5 or -15 points)
    if ufc_com_fighter.get("age") and ufcstats_fighter.dob:
        age_diff = abs(
            ufc_com_fighter["age"] - calculate_age(ufcstats_fighter.dob)
        )
        signals["age_diff"] = age_diff
        if age_diff <= 1:
            bonus_points += 5
        elif age_diff >= 5:
            bonus_points -= 15

    # Signal 4: Weight class plausibility (WEAK - +3 or -10 points)
    if ufc_com_fighter.get("weight") and ufcstats_fighter.weight:
        weight_diff = calculate_weight_difference(
            ufc_com_fighter["weight"],
            ufcstats_fighter.weight
        )
        signals["weight_diff_lbs"] = weight_diff
        if weight_diff <= 10:
            bonus_points += 3
        elif weight_diff >= 40:
            bonus_points -= 10

    final_confidence = name_confidence + bonus_points

    return {
        "base_confidence": name_confidence,
        "bonus_points": bonus_points,
        "final_confidence": min(100, max(0, final_confidence)),
        "signals": signals,
    }
```

### Step 4: Confidence Thresholds

```python
def classify_match(final_confidence: float, confidence_gap: float) -> str:
    """
    Classify match quality and determine action.

    Returns:
        - "auto_high": Auto-accept, high confidence
        - "auto_medium": Auto-accept but flag for spot check
        - "manual_review": Requires human verification
        - "no_match": Skip this fighter
    """
    if final_confidence >= 95 and confidence_gap >= 15:
        return "auto_high"
    elif final_confidence >= 85:
        return "auto_medium"
    elif final_confidence >= 70:
        return "manual_review"
    else:
        return "no_match"
```

### Step 5: Manual Review Output

**File:** `data/processed/ufc_com_matches_manual_review.jsonl`

```jsonl
{
  "ufc_com_fighter": {
    "name": "Bruno Silva",
    "slug": "bruno-silva",
    "division": "Middleweight",
    "record": "23-13-0",
    "age": 35
  },
  "candidates": [
    {
      "id": "12ebd7d157e91701",
      "name": "Bruno Silva",
      "division": "Middleweight",
      "record": "23-13-0",
      "dob": "1989-07-13",
      "final_confidence": 95,
      "signals": {
        "division_match": true,
        "record_similarity": 1.0,
        "age_diff": 0
      }
    },
    {
      "id": "294aa73dbf37d281",
      "name": "Bruno Silva",
      "division": "Flyweight",
      "record": "15-7-2 (1 NC)",
      "dob": "1990-03-16",
      "final_confidence": 45,
      "signals": {
        "division_match": false,
        "record_similarity": 0.2,
        "age_diff": 1
      }
    }
  ],
  "recommended_match": "12ebd7d157e91701",
  "confidence_gap": 50,
  "status": "resolved_duplicate"
}
```

---

## Tiered Enrichment Pipeline

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│ Tier 1: UFC.com Scraping (~3,000 fighters)             │
│   ├─ Birthplace (city + country)                        │
│   └─ Training gym                                       │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Tier 2: Sherdog Nationality (~1,300 fighters)          │
│   └─ Nationality for fighters without UFC.com match     │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Tier 3: Manual Curation (~50-100 fighters)             │
│   └─ Historical legends not on UFC.com                  │
└─────────────────────────────────────────────────────────┘
```

### Coverage Breakdown

```
Total UFCStats fighters: 4,447

Tier 1 (UFC.com match):     ~3,000 fighters (67%)
  ├─ birthplace: ✅
  ├─ training_gym: ✅
  └─ nationality: ✅ (from Sherdog if available)

Tier 2 (Sherdog only):      ~1,300 fighters (30%)
  ├─ birthplace: ❌
  ├─ training_gym: ❌
  └─ nationality: ✅ (from Sherdog)

Tier 3 (Manual):            ~50 fighters (1%)
  ├─ birthplace: ✅ (manual CSV)
  ├─ training_gym: ✅ (manual CSV)
  └─ nationality: ✅ (manual CSV)

No data:                    ~100 fighters (2%)
  └─ Very obscure/data quality issues
```

### Data Quality Tiers

**Tier 1: Complete Data (UFC.com)**
- Birthplace: City + Country
- Training: Gym name
- Confidence: High (automated matching)
- Update frequency: Daily/Weekly

**Tier 2: Partial Data (Sherdog)**
- Nationality only (country-level)
- No birthplace city
- No training location
- Update frequency: Quarterly

**Tier 3: Curated Data (Manual)**
- All fields available
- Highest accuracy
- Update frequency: As needed

---

## Data Loading & Migration

### Alembic Migration

**File:** `backend/db/migrations/versions/XXXXXX_add_fighter_locations.py`

```python
"""Add geographical location fields to fighters table

Revision ID: XXXXXX
Revises: 1f9e5f49e8cc
Create Date: 2025-11-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # Add geographical columns
    op.add_column('fighters', sa.Column('birthplace_city', sa.String(100), nullable=True))
    op.add_column('fighters', sa.Column('birthplace_country', sa.String(100), nullable=True))
    op.add_column('fighters', sa.Column('birthplace', sa.String(255), nullable=True))
    op.add_column('fighters', sa.Column('nationality', sa.String(100), nullable=True))
    op.add_column('fighters', sa.Column('training_gym', sa.String(255), nullable=True))
    op.add_column('fighters', sa.Column('training_city', sa.String(100), nullable=True))
    op.add_column('fighters', sa.Column('training_country', sa.String(100), nullable=True))

    # Add UFC.com cross-reference columns
    op.add_column('fighters', sa.Column('ufc_com_slug', sa.String(255), nullable=True))
    op.add_column('fighters', sa.Column('ufc_com_scraped_at', sa.DateTime(), nullable=True))

    # Add matching metadata columns
    op.add_column('fighters', sa.Column('ufc_com_match_confidence', sa.Float(), nullable=True))
    op.add_column('fighters', sa.Column('ufc_com_match_method', sa.String(20), nullable=True))
    op.add_column('fighters', sa.Column('needs_manual_review', sa.Boolean(),
                                       nullable=False, server_default='false'))

    # Add indexes for common queries
    op.create_index('ix_fighters_birthplace_country', 'fighters', ['birthplace_country'])
    op.create_index('ix_fighters_nationality', 'fighters', ['nationality'])
    op.create_index('ix_fighters_training_city', 'fighters', ['training_city'])
    op.create_index('ix_fighters_training_country', 'fighters', ['training_country'])
    op.create_index('ix_fighters_ufc_com_slug', 'fighters', ['ufc_com_slug'], unique=True)
    op.create_index('ix_fighters_needs_manual_review', 'fighters', ['needs_manual_review'])

    # Composite indexes for common filter combinations
    op.create_index('ix_fighters_birthplace_country_division', 'fighters',
                   ['birthplace_country', 'division'])
    op.create_index('ix_fighters_training_country_division', 'fighters',
                   ['training_country', 'division'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_fighters_training_country_division', 'fighters')
    op.drop_index('ix_fighters_birthplace_country_division', 'fighters')
    op.drop_index('ix_fighters_needs_manual_review', 'fighters')
    op.drop_index('ix_fighters_ufc_com_slug', 'fighters')
    op.drop_index('ix_fighters_training_country', 'fighters')
    op.drop_index('ix_fighters_training_city', 'fighters')
    op.drop_index('ix_fighters_nationality', 'fighters')
    op.drop_index('ix_fighters_birthplace_country', 'fighters')

    # Drop columns
    op.drop_column('fighters', 'needs_manual_review')
    op.drop_column('fighters', 'ufc_com_match_method')
    op.drop_column('fighters', 'ufc_com_match_confidence')
    op.drop_column('fighters', 'ufc_com_scraped_at')
    op.drop_column('fighters', 'ufc_com_slug')
    op.drop_column('fighters', 'training_country')
    op.drop_column('fighters', 'training_city')
    op.drop_column('fighters', 'training_gym')
    op.drop_column('fighters', 'nationality')
    op.drop_column('fighters', 'birthplace')
    op.drop_column('fighters', 'birthplace_country')
    op.drop_column('fighters', 'birthplace_city')
```

### Loading Scripts

**Script 1: Load Tier 1 Data (UFC.com)**

**File:** `scripts/load_ufc_com_locations.py`

```python
"""
Load UFC.com location data into fighters table.

Usage:
    python scripts/load_ufc_com_locations.py --matches data/processed/ufc_com_matches.jsonl
    python scripts/load_ufc_com_locations.py --dry-run  # Preview changes
    python scripts/load_ufc_com_locations.py --auto-only  # Skip manual review items
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
import click

from backend.db.connection import get_session
from backend.db.repositories.fighter_repository import PostgreSQLFighterRepository


@click.command()
@click.option('--matches', type=click.Path(exists=True), required=True,
              help='Path to matches JSONL file')
@click.option('--dry-run', is_flag=True, help='Preview changes without writing')
@click.option('--auto-only', is_flag=True, help='Skip manual review items')
async def load_ufc_com_locations(matches: str, dry_run: bool, auto_only: bool):
    stats = {
        "total_matches": 0,
        "loaded": 0,
        "skipped_manual_review": 0,
        "skipped_low_confidence": 0,
        "errors": 0,
    }

    async with get_session() as session:
        repo = PostgreSQLFighterRepository(session)

        with open(matches) as f:
            for line in f:
                match = json.loads(line)
                stats["total_matches"] += 1

                # Skip if needs manual review and auto_only is set
                if auto_only and match.get("needs_manual_review"):
                    stats["skipped_manual_review"] += 1
                    continue

                # Skip low confidence matches
                if match["confidence"] < 70:
                    stats["skipped_low_confidence"] += 1
                    continue

                # Load UFC.com fighter data
                ufc_com_file = Path("data/processed/ufc_com_fighters") / f"{match['ufc_com_slug']}.json"

                if not ufc_com_file.exists():
                    click.echo(f"⚠️  Missing UFC.com data for {match['ufc_com_slug']}")
                    stats["errors"] += 1
                    continue

                with open(ufc_com_file) as uf:
                    ufc_com_data = json.load(uf)

                if dry_run:
                    click.echo(f"Would update {match['ufcstats_id']} with:")
                    click.echo(f"  Birthplace: {ufc_com_data.get('birthplace')}")
                    click.echo(f"  Training gym: {ufc_com_data.get('training_gym')}")
                else:
                    try:
                        await repo.update_fighter_location(
                            fighter_id=match["ufcstats_id"],
                            birthplace=ufc_com_data.get("birthplace"),
                            birthplace_city=ufc_com_data.get("birthplace_city"),
                            birthplace_country=ufc_com_data.get("birthplace_country"),
                            training_gym=ufc_com_data.get("training_gym"),
                            ufc_com_slug=match["ufc_com_slug"],
                            ufc_com_match_confidence=match["confidence"],
                            ufc_com_match_method=match["method"],
                            ufc_com_scraped_at=datetime.utcnow(),
                            needs_manual_review=match.get("needs_manual_review", False),
                        )
                        stats["loaded"] += 1

                        if stats["loaded"] % 100 == 0:
                            click.echo(f"Loaded {stats['loaded']} fighters...")

                    except Exception as e:
                        click.echo(f"❌ Error updating {match['ufcstats_id']}: {e}")
                        stats["errors"] += 1

        if not dry_run:
            await session.commit()

    click.echo("\n" + "="*50)
    click.echo("SUMMARY")
    click.echo("="*50)
    for key, value in stats.items():
        click.echo(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(load_ufc_com_locations())
```

**Script 2: Load Tier 2 Data (Sherdog)**

**File:** `scripts/load_sherdog_nationality.py`

```python
"""
Load Sherdog nationality for fighters without UFC.com matches.

Usage:
    python scripts/load_sherdog_nationality.py
"""

import asyncio
import json
from pathlib import Path
import click

from backend.db.connection import get_session
from backend.db.repositories.fighter_repository import PostgreSQLFighterRepository


@click.command()
async def load_sherdog_nationality():
    stats = {"total": 0, "loaded": 0, "no_data": 0, "errors": 0}

    async with get_session() as session:
        repo = PostgreSQLFighterRepository(session)

        # Find fighters without UFC.com data
        fighters = await repo.get_fighters_without_ufc_com_data()
        stats["total"] = len(fighters)

        click.echo(f"Found {stats['total']} fighters without UFC.com data")

        for fighter in fighters:
            if not fighter.sherdog_id:
                stats["no_data"] += 1
                continue

            # Load Sherdog data
            sherdog_file = Path("data/processed/sherdog_fighters") / f"{fighter.sherdog_id}.json"

            if not sherdog_file.exists():
                stats["no_data"] += 1
                continue

            with open(sherdog_file) as f:
                sherdog_data = json.load(f)

            nationality = sherdog_data.get("nationality")

            if nationality:
                try:
                    await repo.update_fighter_nationality(
                        fighter_id=fighter.id,
                        nationality=nationality
                    )
                    stats["loaded"] += 1

                    if stats["loaded"] % 100 == 0:
                        click.echo(f"Loaded {stats['loaded']} nationalities...")

                except Exception as e:
                    click.echo(f"❌ Error updating {fighter.id}: {e}")
                    stats["errors"] += 1
            else:
                stats["no_data"] += 1

        await session.commit()

    click.echo("\n" + "="*50)
    click.echo("SUMMARY")
    click.echo("="*50)
    for key, value in stats.items():
        click.echo(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(load_sherdog_nationality())
```

**Script 3: Load Tier 3 Data (Manual)**

**File:** `scripts/load_manual_curated_data.py`

```python
"""
Load manually curated location data for historical fighters.

Usage:
    python scripts/load_manual_curated_data.py --csv data/manual/legends_locations.csv
"""

import asyncio
import csv
import click

from backend.db.connection import get_session
from backend.db.repositories.fighter_repository import PostgreSQLFighterRepository


@click.command()
@click.option('--csv', 'csv_file', type=click.Path(exists=True), required=True,
              help='Path to CSV file with manual data')
async def load_manual_curated_data(csv_file: str):
    stats = {"total": 0, "loaded": 0, "errors": 0}

    async with get_session() as session:
        repo = PostgreSQLFighterRepository(session)

        with open(csv_file) as f:
            reader = csv.DictReader(f)

            for row in reader:
                stats["total"] += 1

                try:
                    await repo.update_fighter_location(
                        fighter_id=row["ufcstats_id"],
                        birthplace=row.get("birthplace"),
                        nationality=row.get("nationality"),
                        training_gym=row.get("training_gym"),
                        ufc_com_match_method="manual",
                        ufc_com_match_confidence=100.0,
                    )
                    stats["loaded"] += 1
                    click.echo(f"✅ Loaded manual data for {row['name']}")

                except Exception as e:
                    click.echo(f"❌ Error loading {row['name']}: {e}")
                    stats["errors"] += 1

        await session.commit()

    click.echo("\n" + "="*50)
    click.echo("SUMMARY")
    click.echo("="*50)
    for key, value in stats.items():
        click.echo(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(load_manual_curated_data())
```

### Makefile Targets

```makefile
# Makefile additions

.PHONY: scrape-ufc-com-locations
scrape-ufc-com-locations:  ## Scrape UFC.com for fighter locations
	@echo "Scraping UFC.com athletes list..."
	.venv/bin/scrapy crawl ufc_com_athletes -o data/processed/ufc_com_athletes_list.jsonl
	@echo "Scraping individual athlete profiles..."
	.venv/bin/scrapy crawl ufc_com_athlete_detail -a input=data/processed/ufc_com_athletes_list.jsonl

.PHONY: match-ufc-com-fighters
match-ufc-com-fighters:  ## Run fuzzy matching for UFC.com fighters
	python scripts/match_ufc_com_fighters.py \
		--ufc-com data/processed/ufc_com_fighters/ \
		--output data/processed/ufc_com_matches.jsonl

.PHONY: load-fighter-locations
load-fighter-locations:  ## Load fighter location data (all tiers)
	@echo "Loading Tier 1: UFC.com locations..."
	python scripts/load_ufc_com_locations.py --matches data/processed/ufc_com_matches.jsonl --auto-only
	@echo "Loading Tier 2: Sherdog nationality..."
	python scripts/load_sherdog_nationality.py
	@echo "Done! Run 'python scripts/review_matches.py' for manual verification."

.PHONY: enrich-fighter-locations
enrich-fighter-locations: db-upgrade scrape-ufc-com-locations match-ufc-com-fighters load-fighter-locations  ## Complete pipeline: scrape → match → load
```

---

## Update & Refresh Strategy

### Update Types & Frequencies

**Type 1: New Fighters** (UFC signs new athletes)
- **Frequency:** Weekly
- **Strategy:** Scrape UFC.com athletes list, match new slugs
- **Cron:** `0 5 * * 1` (Monday 5am)

**Type 2: Location Changes** (Fighter moves gyms)
- **Frequency:** Monthly for active fighters
- **Strategy:** Re-scrape high-priority fighters
- **Cron:** `0 3 1 * *` (1st of month, 3am)

**Type 3: Data Corrections** (UFC.com fixes wrong info)
- **Frequency:** Quarterly for all fighters
- **Strategy:** Full refresh of stale data (>90 days)
- **Cron:** `0 4 1 */3 *` (Quarterly, 1st at 4am)

### Refresh Priority Logic

```python
def should_refresh_fighter(fighter: Fighter) -> bool:
    """Determine if a fighter's location data needs refreshing."""

    # Never scraped - needs initial data
    if not fighter.ufc_com_scraped_at:
        return True

    # Calculate staleness
    days_since_scrape = (datetime.utcnow() - fighter.ufc_com_scraped_at).days

    # Active fighters: refresh more frequently (30 days)
    if fighter.is_active and days_since_scrape > 30:
        return True

    # Recent fighters: refresh quarterly (90 days)
    if fighter.last_fight_date:
        days_since_fight = (datetime.utcnow().date() - fighter.last_fight_date).days
        if days_since_fight < 365 and days_since_scrape > 90:
            return True

    # All fighters: refresh if very stale (180 days)
    if days_since_scrape > 180:
        return True

    # Has manual review flag - skip automatic updates
    if fighter.needs_manual_review:
        return False

    return False


def determine_update_priority(fighter: Fighter) -> str:
    """Prioritize which fighters to update first."""

    # High priority: Active fighters with winning streak
    if fighter.is_active and fighter.current_streak_count > 0:
        return "high"

    # Medium priority: Inactive but recent (fought in last year)
    if fighter.last_fight_date:
        days_since_fight = (datetime.utcnow().date() - fighter.last_fight_date).days
        if days_since_fight < 365:
            return "medium"

    # Low priority: Historical/retired fighters
    return "low"
```

### Change Detection & Logging

```python
def detect_location_changes(old_fighter: Fighter, new_data: dict) -> dict:
    """Detect what changed between old and new data."""

    changes = {
        "has_changes": False,
        "birthplace_changed": False,
        "gym_changed": False,
        "changes_detail": [],
    }

    # Check birthplace
    if old_fighter.birthplace != new_data.get("birthplace"):
        changes["has_changes"] = True
        changes["birthplace_changed"] = True
        changes["changes_detail"].append({
            "field": "birthplace",
            "old": old_fighter.birthplace,
            "new": new_data.get("birthplace"),
        })

    # Check training gym
    if old_fighter.training_gym != new_data.get("training_gym"):
        changes["has_changes"] = True
        changes["gym_changed"] = True
        changes["changes_detail"].append({
            "field": "training_gym",
            "old": old_fighter.training_gym,
            "new": new_data.get("training_gym"),
        })

    return changes
```

### Change Log Format

**File:** `data/logs/location_changes_YYYY-MM-DD.jsonl`

```jsonl
{
  "timestamp": "2025-01-15T10:30:00Z",
  "fighter_id": "abc123",
  "fighter_name": "Dustin Poirier",
  "change_type": "gym_change",
  "field": "training_gym",
  "old_value": "American Top Team",
  "new_value": "Poirier MMA",
  "source": "ufc.com",
  "confidence": 100.0
}
```

### Cron Schedule

```bash
# crontab -e

# Daily: Refresh high-priority fighters (active, winning streak)
0 2 * * * cd /path/to/ufc-pokedex && make refresh-locations-high-priority

# Weekly: Refresh medium-priority + check for new UFC.com fighters
0 3 * * 0 cd /path/to/ufc-pokedex && make refresh-locations-medium-priority
0 5 * * 1 cd /path/to/ufc-pokedex && make scrape-ufc-com-new-fighters

# Monthly: Refresh all stale data (>90 days old)
0 4 1 * * cd /path/to/ufc-pokedex && make refresh-locations-all
```

### Manual Override System

**File:** `data/manual/location_overrides.json`

```json
{
  "overrides": [
    {
      "fighter_id": "abc123",
      "fighter_name": "Conor McGregor",
      "override_reason": "UFC.com data incorrect, verified via Wikipedia",
      "fields": {
        "birthplace": "Crumlin, Dublin, Ireland",
        "training_gym": "SBG Ireland"
      },
      "do_not_auto_update": true,
      "verified_by": "admin",
      "verified_at": "2025-01-15"
    }
  ]
}
```

**Usage:**
```bash
# Apply manual overrides after auto-updates
python scripts/apply_manual_overrides.py --file data/manual/location_overrides.json
```

---

## Rate Limiting & Politeness

### UFC.com Infrastructure

**Observed:**
- ✅ Varnish CDN (x-cache headers)
- ✅ 24-hour cache TTL
- ✅ Drupal 10 backend
- ✅ Pantheon hosting
- ❌ No explicit rate limit headers

**Implications:**
- Cached responses are safe (don't hit origin)
- Need conservative rate limits
- Respect robots.txt
- Use polite User-Agent

### Scrapy Configuration

```python
# scraper/settings.py

UFC_COM_SETTINGS = {
    # Download delay: 2.5 seconds between requests
    "DOWNLOAD_DELAY": 2.5,

    # Randomize delay (1.25s - 3.75s)
    "RANDOMIZE_DOWNLOAD_DELAY": True,

    # Limit concurrent requests
    "CONCURRENT_REQUESTS": 8,
    "CONCURRENT_REQUESTS_PER_DOMAIN": 1,  # Only 1 to UFC.com at a time

    # AutoThrottle: Adapt to server speed
    "AUTOTHROTTLE_ENABLED": True,
    "AUTOTHROTTLE_START_DELAY": 2.0,
    "AUTOTHROTTLE_MAX_DELAY": 60.0,
    "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.5,
    "AUTOTHROTTLE_DEBUG": True,

    # Respect robots.txt
    "ROBOTSTXT_OBEY": True,

    # User agent
    "USER_AGENT": "UFC-Pokedex-Bot/1.0 (+https://github.com/user/ufc-pokedex; contact@example.com)",

    # Retry settings
    "RETRY_ENABLED": True,
    "RETRY_TIMES": 3,
    "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],

    # HTTP caching (avoid re-scraping)
    "HTTPCACHE_ENABLED": True,
    "HTTPCACHE_EXPIRATION_SECS": 86400,  # 24 hours

    # Download timeout
    "DOWNLOAD_TIMEOUT": 30,
}
```

### Batch Processing Strategy

**Initial scrape (3,000 fighters):**

```python
# Scrape in batches to avoid overwhelming server

BATCH_SIZE = 100 fighters
BATCH_DELAY = 60 seconds between batches
DOWNLOAD_DELAY = 2.5 seconds per request

Total batches: 30
Time per batch: (100 × 2.5s) + 60s = ~310s
Total time: 30 × 310s = 9,300s ≈ 2.5 hours
```

**Script:** `scripts/scrape_ufc_com_batched.py`

```python
async def scrape_in_batches(
    fighters: list[dict],
    batch_size: int = 100,
    batch_delay: int = 60,
):
    total_batches = (len(fighters) + batch_size - 1) // batch_size

    for i in range(0, len(fighters), batch_size):
        batch = fighters[i:i + batch_size]
        batch_num = (i // batch_size) + 1

        logger.info(f"Batch {batch_num}/{total_batches} ({len(batch)} fighters)")

        subprocess.run([
            ".venv/bin/scrapy", "crawl", "ufc_com_athlete_detail",
            "-a", f"slugs={','.join([f['slug'] for f in batch])}",
            "-o", f"data/processed/ufc_com_batch_{batch_num}.jsonl"
        ])

        if batch_num < total_batches:
            logger.info(f"Waiting {batch_delay}s before next batch...")
            time.sleep(batch_delay)
```

### Exponential Backoff for Errors

**Middleware:** `scraper/middlewares/retry.py`

```python
class UFCComRetryMiddleware(RetryMiddleware):
    """Custom retry logic with exponential backoff."""

    def process_response(self, request, response, spider):
        # Detect rate limiting
        if response.status in [429, 503]:
            retry_after = response.headers.get('Retry-After')

            if retry_after:
                delay = int(retry_after)
            else:
                # Exponential backoff
                retry_count = request.meta.get('retry_times', 0)
                delay = min(2 ** retry_count, 300)  # Max 5 minutes

            spider.logger.warning(f"Rate limited! Waiting {delay}s")
            time.sleep(delay)

            return self._retry(request, "rate_limit", spider) or response

        return super().process_response(request, response, spider)
```

### Politeness Checklist

```python
# ✅ Respect robots.txt
ROBOTSTXT_OBEY = True

# ✅ Identify yourself
USER_AGENT = "UFC-Pokedex-Bot/1.0 (+URL; contact@example.com)"

# ✅ Rate limit aggressively
DOWNLOAD_DELAY = 2.5

# ✅ Limit concurrency
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# ✅ Adapt to server speed
AUTOTHROTTLE_ENABLED = True

# ✅ Exponential backoff
RetryMiddleware with backoff

# ✅ Scrape during off-peak hours
Cron: 2am-6am local time

# ✅ Cache responses
HTTPCACHE_ENABLED = True
```

---

## API Endpoints

### Existing Endpoint Enhancements

**GET `/fighters/` - Add location filters**

```python
@router.get("/", response_model=FightersListResponse)
async def list_fighters(
    # Existing filters
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    division: str | None = Query(default=None),
    stance: str | None = Query(default=None),

    # NEW: Location filters
    birthplace_country: str | None = Query(default=None),
    birthplace_city: str | None = Query(default=None),
    nationality: str | None = Query(default=None),
    training_country: str | None = Query(default=None),
    training_city: str | None = Query(default=None),
    training_gym: str | None = Query(default=None),
    has_location_data: bool | None = Query(default=None),
):
    """
    List fighters with location filtering.

    Examples:
        /fighters/?birthplace_country=Ireland
        /fighters/?training_gym=American Kickboxing Academy
        /fighters/?nationality=Brazilian&division=Lightweight
    """
```

### New Statistics Endpoints

**GET `/stats/countries` - Country breakdown**

```python
@router.get("/countries", response_model=CountryStatsResponse)
async def get_country_stats(
    group_by: Literal["birthplace", "training", "nationality"] = Query(default="birthplace"),
    min_fighters: int = Query(default=1, ge=1),
):
    """
    Get fighter count by country.

    Response:
        {
          "group_by": "birthplace",
          "countries": [
            {"country": "United States", "count": 1450, "percentage": 48.3},
            {"country": "Brazil", "count": 420, "percentage": 14.0},
            ...
          ],
          "total_fighters": 3000
        }
    """
```

**GET `/stats/cities` - City breakdown**

```python
@router.get("/cities", response_model=CityStatsResponse)
async def get_city_stats(
    group_by: Literal["birthplace", "training"] = Query(default="training"),
    country: str | None = Query(default=None),
    min_fighters: int = Query(default=5, ge=1),
):
    """
    Get fighter count by city.

    Examples:
        /stats/cities?group_by=training&min_fighters=10
        /stats/cities?group_by=birthplace&country=United States
    """
```

**GET `/stats/gyms` - Top gyms**

```python
@router.get("/gyms", response_model=GymStatsResponse)
async def get_gym_stats(
    country: str | None = Query(default=None),
    min_fighters: int = Query(default=5, ge=1),
    sort_by: Literal["fighters", "name"] = Query(default="fighters"),
):
    """
    Get fighter count by training gym.

    Response:
        {
          "gyms": [
            {
              "gym": "American Top Team",
              "city": "Coconut Creek",
              "country": "United States",
              "fighter_count": 78,
              "notable_fighters": ["Amanda Nunes", "Dustin Poirier"]
            },
            ...
          ]
        }
    """
```

### Search Enhancement

**GET `/search/` - Include location matching**

```python
@router.get("/", response_model=SearchResponse)
async def search_fighters(
    q: str = Query(..., min_length=1),
    include_locations: bool = Query(default=True),
):
    """
    Search fighters by name, nickname, OR location.

    Examples:
        /search/?q=dublin      # Finds fighters from Dublin
        /search/?q=aka         # Finds fighters from AKA gym
        /search/?q=brazilian   # Finds Brazilian fighters
    """
```

### Repository Methods

```python
# backend/db/repositories/fighter_repository.py

class PostgreSQLFighterRepository:

    async def list_fighters(
        self,
        limit: int,
        offset: int,
        filters: FighterFilters | None = None,
    ) -> list[Fighter]:
        """List fighters with location filtering."""
        query = select(Fighter)

        if filters:
            if filters.birthplace_country:
                query = query.where(Fighter.birthplace_country == filters.birthplace_country)

            if filters.training_gym:
                query = query.where(Fighter.training_gym.ilike(f"%{filters.training_gym}%"))

            # ... more filters

        return await self.session.execute(query.limit(limit).offset(offset))

    async def get_country_stats(self, group_by: str) -> list[dict]:
        """Get fighter count by country."""
        # Implementation using SQLAlchemy func.count() and GROUP BY

    async def get_gym_stats(self) -> list[dict]:
        """Get fighter count by gym."""
        # Implementation using GROUP BY training_gym
```

---

## Frontend UI Components

### Component 1: Enhanced Fighter Card

**File:** `frontend/src/components/fighter/EnhancedFighterCard.tsx`

```tsx
import { MapPin, Globe, Dumbbell } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

export function EnhancedFighterCard({ fighter }: { fighter: Fighter }) {
  return (
    <Card>
      {/* Existing card content... */}

      {/* NEW: Location badges */}
      <CardContent className="pt-4 space-y-2">
        {fighter.birthplace && (
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-muted-foreground" />
            <Badge variant="outline" className="gap-1">
              <span className="text-xs text-muted-foreground">Born:</span>
              <span className="font-medium">{fighter.birthplace}</span>
            </Badge>
          </div>
        )}

        {fighter.training_gym && (
          <div className="flex items-center gap-2">
            <Dumbbell className="h-4 w-4 text-muted-foreground" />
            <Badge variant="secondary" className="gap-1">
              <span className="text-xs text-muted-foreground">Trains at:</span>
              <span className="font-medium">{fighter.training_gym}</span>
            </Badge>
          </div>
        )}

        {!fighter.birthplace && fighter.nationality && (
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 text-muted-foreground" />
            <Badge variant="outline" className="gap-1">
              <span className="font-medium">{fighter.nationality}</span>
            </Badge>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

### Component 2: Location Filters Sidebar

**File:** `frontend/src/components/filters/LocationFilters.tsx`

```tsx
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';

export function LocationFilters({
  filters,
  onFilterChange,
  onClear,
  availableCountries,
  availableGyms,
}) {
  const handleClear = () => {
    if (onClear) {
      onClear();
    } else {
      onFilterChange({});
    }
  };

  return (
    <div className="space-y-4 p-4 border rounded-lg">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Filter by Location</h3>
        <Button variant="ghost" size="sm" onClick={handleClear}>
          <X className="h-4 w-4 mr-1" />
          Clear
        </Button>
      </div>

      {/* Birthplace Country */}
      <div className="space-y-2">
        <Label>Birthplace Country</Label>
        <Select value={filters.birthplace_country || ''} onValueChange={...}>
          <SelectTrigger>
            <SelectValue placeholder="All countries" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All countries</SelectItem>
            {availableCountries.map(country => (
              <SelectItem key={country} value={country}>{country}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Training Gym */}
      <div className="space-y-2">
        <Label>Training Gym</Label>
        <Select value={filters.training_gym || ''} onValueChange={...}>
          {/* Similar to above */}
        </Select>
      </div>
    </div>
  );
}
```

> Parent containers should pass `onClear={() => onFilterChange(defaultFilters)}` when they maintain additional query state; otherwise the component falls back to wiping all filters locally.

### Component 3: Country Statistics Card

**File:** `frontend/src/components/stats/CountryStatsCard.tsx`

```tsx
import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import client from '@/lib/api-client';
import { Flag } from 'lucide-react';

export function CountryStatsCard() {
  const [stats, setStats] = useState<CountryStats[] | null>(null);

  useEffect(() => {
    async function fetchStats() {
      const { data } = await client.GET('/stats/countries', {
        params: { query: { group_by: 'birthplace', min_fighters: 5 } }
      });
      if (data) setStats(data.countries.slice(0, 10));
    }
    fetchStats();
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Flag className="h-5 w-5" />
          Top Countries (by Birthplace)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {stats?.map((stat, index) => (
            <div key={stat.country} className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="text-2xl font-bold">#{index + 1}</div>
                <div>
                  <div className="font-semibold">{stat.country}</div>
                  <div className="text-sm text-muted-foreground">
                    {stat.percentage.toFixed(1)}% of roster
                  </div>
                </div>
              </div>
              <Badge variant="secondary">{stat.count}</Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
```

### Component 4: Top Gyms Widget

**File:** `frontend/src/components/stats/TopGymsWidget.tsx`

```tsx
import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Dumbbell } from 'lucide-react';
import client from '@/lib/api-client';

export function TopGymsWidget() {
  const [gyms, setGyms] = useState<GymStats[] | null>(null);

  useEffect(() => {
    async function fetchGyms() {
      const { data } = await client.GET('/stats/gyms', {
        params: { query: { min_fighters: 10, sort_by: 'fighters' } }
      });
      if (data) setGyms(data.gyms.slice(0, 5));
    }
    fetchGyms();
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Dumbbell className="h-5 w-5" />
          Elite Training Gyms
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {gyms?.map((gym) => (
            <div key={gym.gym} className="flex items-start gap-3">
              <Avatar>
                <AvatarFallback>{gym.gym.substring(0, 2).toUpperCase()}</AvatarFallback>
              </Avatar>
              <div className="flex-1">
                <div className="font-semibold">{gym.gym}</div>
                <div className="text-sm text-muted-foreground">
                  {gym.city}, {gym.country}
                </div>
                <div className="text-xs text-muted-foreground">
                  {gym.fighter_count} fighters
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
```

### Page Updates

**Enhanced Fighter Detail Page:**

```tsx
// frontend/app/fighters/[id]/page.tsx

export default function FighterDetailPage({ params }) {
  const { data: fighter } = useFighter(params.id);

  return (
    <div className="container">
      {/* Existing content */}

      {/* NEW: Location Information Card */}
      {(fighter.birthplace || fighter.training_gym) && (
        <Card>
          <CardHeader>
            <CardTitle>Location Information</CardTitle>
          </CardHeader>
          <CardContent>
            {fighter.birthplace && (
              <div>
                <h4>Birthplace</h4>
                <Badge>{fighter.birthplace}</Badge>
              </div>
            )}

            {fighter.training_gym && (
              <div>
                <h4>Training</h4>
                <div className="flex items-center gap-2">
                  <Dumbbell className="h-4 w-4" />
                  <span>{fighter.training_gym}</span>
                </div>
              </div>
            )}

            {/* Links to filtered views */}
            <Link href={`/fighters?birthplace_country=${fighter.birthplace_country}`}>
              View all fighters from {fighter.birthplace_country} →
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

**New Explore Page:**

```tsx
// frontend/app/explore/page.tsx

export default function ExplorePage() {
  return (
    <div className="container">
      <h1>Explore by Location</h1>

      <Tabs defaultValue="countries">
        <TabsList>
          <TabsTrigger value="countries">Countries</TabsTrigger>
          <TabsTrigger value="cities">Cities</TabsTrigger>
          <TabsTrigger value="gyms">Gyms</TabsTrigger>
        </TabsList>

        <TabsContent value="countries">
          <CountryStatsCard />
        </TabsContent>

        <TabsContent value="gyms">
          <TopGymsWidget />
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

### Mobile Responsive Design

```tsx
// Desktop: Full info with icons
<div className="hidden md:flex items-center gap-2">
  <MapPin className="h-4 w-4" />
  <Badge>{fighter.birthplace}</Badge>
</div>

// Mobile: Compact badges only
<div className="flex md:hidden flex-wrap gap-1">
  <Badge variant="outline" className="text-xs">
    📍 {fighter.birthplace_city || fighter.birthplace_country}
  </Badge>
</div>
```

---

## Implementation Plan

### Phase 1: Database Setup (Week 1)

**Tasks:**
- [ ] Create Alembic migration for new columns
- [ ] Run migration on development database
- [ ] Update `Fighter` model in `backend/db/models/__init__.py`
- [ ] Update Pydantic schemas in `backend/schemas/fighter.py`
- [ ] Run `make types-generate` to update frontend types

**Deliverables:**
- Migration file applied
- Database schema updated
- TypeScript types regenerated

**Testing:**
- [ ] Verify migration up/down works
- [ ] Test indexes created correctly
- [ ] Confirm no breaking changes to existing queries

---

### Phase 2: UFC.com Scraping (Week 2)

**Tasks:**
- [ ] Create `ufc_com_athletes` spider
- [ ] Create `ufc_com_athlete_detail` spider
- [ ] Implement parsing logic for bio fields
- [ ] Add Scrapy settings for UFC.com
- [ ] Create retry middleware with backoff
- [ ] Test scrapers on sample fighters

**Deliverables:**
- `scraper/spiders/ufc_com_athletes.py`
- `scraper/spiders/ufc_com_athlete_detail.py`
- `scraper/middlewares/retry.py`
- Sample output files in `data/processed/`

**Testing:**
- [ ] Scrape 10 fighters and verify data quality
- [ ] Test rate limiting (check logs for delays)
- [ ] Verify cache headers detected correctly

---

### Phase 3: Fuzzy Matching (Week 3)

**Tasks:**
- [ ] Create `scripts/match_ufc_com_fighters.py`
- [ ] Implement name normalization
- [ ] Implement multi-algorithm matching
- [ ] Implement duplicate resolution logic
- [ ] Create manual review CLI tool
- [ ] Test on known duplicates (Bruno Silva, etc.)

**Deliverables:**
- Matching script with CLI interface
- Manual review JSONL output
- Review tool for manual verification

**Testing:**
- [ ] Test on 100 fighters, verify >90% match rate
- [ ] Manually verify duplicate handling
- [ ] Check confidence scores are reasonable

---

### Phase 4: Data Loading (Week 4)

**Tasks:**
- [ ] Create `scripts/load_ufc_com_locations.py`
- [ ] Create `scripts/load_sherdog_nationality.py`
- [ ] Create `scripts/load_manual_curated_data.py`
- [ ] Create `scripts/review_matches.py` CLI tool
- [x] Build `data/manual/gym_locations.csv` seed + `scripts/suggest_gym_location.py`
- [ ] Add Makefile targets
- [ ] Run full data load on development database

**Deliverables:**
- All loading scripts functional
- Gym lookup CSV with ≥500 vetted gyms
- Makefile targets working
- Development database populated

**Testing:**
- [ ] Dry-run all scripts
- [ ] Load 100 fighters and verify data
- [ ] Test manual override system
- [ ] Verify new gyms fall back to suggestion workflow (no direct null writes)

---

### Phase 5: Backend API (Week 5)

**Tasks:**
- [ ] Update `GET /fighters/` with location filters
- [ ] Create `GET /stats/countries` endpoint
- [ ] Create `GET /stats/cities` endpoint
- [ ] Create `GET /stats/gyms` endpoint
- [ ] Update search endpoint with location matching
- [ ] Update repository methods
- [ ] Update Pydantic response models

**Deliverables:**
- All API endpoints functional
- OpenAPI schema updated
- Repository layer complete

**Testing:**
- [ ] Test all filter combinations
- [ ] Verify index usage (EXPLAIN queries)
- [ ] Load test with 1000 concurrent requests

---

### Phase 6: Frontend UI (Week 6)

**Tasks:**
- [ ] Update `EnhancedFighterCard` with location badges
- [ ] Create `LocationFilters` component
- [ ] Create `CountryStatsCard` component
- [ ] Create `TopGymsWidget` component
- [ ] Update fighter detail page
- [ ] Create `/explore` page
- [ ] Add quick filter badges to home page

**Deliverables:**
- All UI components functional
- Pages updated with location data
- Mobile responsive design

**Testing:**
- [ ] Manual testing on desktop/mobile
- [ ] Verify all links work
- [ ] Test filter combinations

---

### Phase 7: Update Automation (Week 7)

**Tasks:**
- [ ] Create `scripts/refresh_fighter_locations.py`
- [ ] Implement priority-based refresh logic
- [ ] Create change detection and logging
- [ ] Set up cron jobs
- [ ] Create monitoring script
- [ ] Document manual override process

**Deliverables:**
- Refresh script with CLI options
- Cron schedule configured
- Change logs generated

**Testing:**
- [ ] Test refresh on 50 fighters
- [ ] Verify change detection works
- [ ] Test cron jobs in staging

---

### Phase 8: Production Deployment (Week 8)

**Tasks:**
- [ ] Run initial data scrape (3,000 fighters)
- [ ] Review manual review queue
- [ ] Load all data to production database
- [ ] Deploy backend API changes
- [ ] Deploy frontend UI changes
- [ ] Set up production cron jobs
- [ ] Monitor for 1 week

**Deliverables:**
- Production database populated
- All services deployed
- Monitoring in place

**Testing:**
- [ ] Smoke test all endpoints
- [ ] Verify data quality in production
- [ ] Monitor error rates

---

## Open Questions

### Technical Questions

1. **Geocoding for Map Visualization**
   - Do we want to add lat/lng coordinates for cities?
   - Service to use: Google Maps API, Mapbox, or manual CSV?
   - Cost implications?

2. **Training Location Parsing**
   - Should we parse city/country from gym names automatically?
   - Example: "American Kickboxing Academy" → "San Jose, California"
   - Or leave as manual data entry?

3. **Historical Data Versioning**
   - Should we track gym changes over time?
   - Create `fighter_location_history` table?
   - Or just keep latest + change logs?

4. **Sherdog Integration**
   - Sherdog returns 403 on some requests - need rotating proxies?
   - Or acceptable to have gaps in nationality data?

### Product Questions

1. **Map Visualization Priority**
   - Is interactive map high priority or future enhancement?
   - If high priority, which library? (Mapbox, Leaflet, Google Maps)

2. **Location Data Completeness**
   - Is 67% coverage (Tier 1) acceptable?
   - Or should we prioritize manual curation for more fighters?

3. **User-Generated Content**
   - Allow users to submit location corrections?
   - Crowdsource missing data?
   - Moderation workflow?

4. **Performance Budget**
   - What's acceptable query time for location filters?
   - Current estimate: <100ms for indexed queries
   - Need caching layer (Redis)?

### Business Questions

1. **Scraping Legal/Ethical Concerns**
   - UFC.com terms of service review?
   - Need to contact UFC for permission?
   - Acceptable use as non-commercial project?

2. **Data Refresh Budget**
   - How often should we refresh data?
   - Current plan: Daily (high priority), Weekly (medium), Monthly (all)
   - Server costs implications?

3. **Feature Prioritization**
   - Which features are MVP?
   - Which can be deferred to future iterations?

---

## Appendix

### A. Sample Commands

**Run full pipeline:**
```bash
# 1. Run migration
make db-upgrade

# 2. Scrape UFC.com
make scrape-ufc-com-locations

# 3. Match fighters
make match-ufc-com-fighters

# 4. Review matches (manual)
python scripts/review_matches.py --input data/processed/ufc_com_matches_manual_review.jsonl

# 5. Load data
make load-fighter-locations

# 6. Verify
python scripts/monitor_location_data_health.py
```

**Incremental updates:**
```bash
# Refresh high-priority fighters
make refresh-locations-high-priority

# Check for new fighters
make scrape-ufc-com-new-fighters
```

### B. File Structure

```
ufc-pokedex/
├── backend/
│   ├── db/
│   │   ├── models/__init__.py           # Updated Fighter model
│   │   ├── migrations/versions/
│   │   │   └── XXXXXX_add_fighter_locations.py
│   │   └── repositories/
│   │       └── fighter_repository.py    # New location methods
│   ├── api/
│   │   ├── fighters.py                  # Updated with location filters
│   │   └── stats.py                     # NEW: Location stats endpoints
│   └── schemas/
│       ├── fighter.py                   # Updated with location fields
│       └── stats.py                     # NEW: Location stats schemas
├── scraper/
│   ├── spiders/
│   │   ├── ufc_com_athletes.py          # NEW: Athletes list spider
│   │   └── ufc_com_athlete_detail.py    # NEW: Athlete detail spider
│   └── middlewares/
│       └── retry.py                     # NEW: Retry with backoff
├── scripts/
│   ├── match_ufc_com_fighters.py        # NEW: Fuzzy matching
│   ├── load_ufc_com_locations.py        # NEW: Load Tier 1 data
│   ├── load_sherdog_nationality.py      # NEW: Load Tier 2 data
│   ├── load_manual_curated_data.py      # NEW: Load Tier 3 data
│   ├── refresh_fighter_locations.py     # NEW: Incremental updates
│   ├── review_matches.py                # NEW: Manual review CLI
│   ├── suggest_gym_location.py          # NEW: Gym city/country suggestions
│   └── scrape_ufc_com_batched.py        # NEW: Batch scraping
├── frontend/
│   ├── src/
│   │   └── components/
│   │       ├── fighter/
│   │       │   └── EnhancedFighterCard.tsx  # Updated with location badges
│   │       ├── filters/
│   │       │   └── LocationFilters.tsx      # NEW: Location filter sidebar
│   │       └── stats/
│   │           ├── CountryStatsCard.tsx     # NEW: Country breakdown
│   │           └── TopGymsWidget.tsx        # NEW: Top gyms widget
│   └── app/
│       ├── fighters/[id]/page.tsx           # Updated with location section
│       └── explore/page.tsx                 # NEW: Location exploration page
├── data/
│   ├── processed/
│   │   ├── ufc_com_athletes_list.jsonl      # Scraped athletes
│   │   ├── ufc_com_fighters/{slug}.json     # Scraped profiles
│   │   ├── ufc_com_matches.jsonl            # Match results
│   │   └── ufc_com_matches_manual_review.jsonl
│   ├── manual/
│   │   ├── legends_locations.csv            # Manual curation
│   │   ├── gym_locations.csv                # Canonical gym lookup
│   │   └── location_overrides.json          # Manual overrides
│   └── logs/
│       └── location_changes_YYYY-MM-DD.jsonl
└── docs/
    └── plans/
        └── 2025-11-11-fighter-geographical-data-design.md  # This document
```

### C. Dependencies

**Python:**
```toml
# pyproject.toml additions

[project.dependencies]
rapidfuzz = "^3.0.0"      # Fuzzy string matching
unidecode = "^1.3.0"      # Unicode normalization
click = "^8.1.0"          # CLI tools
```

**Frontend:**
```json
// package.json additions (already have most)

{
  "dependencies": {
    "lucide-react": "^0.263.1"  // Icons (MapPin, Globe, Dumbbell)
  }
}
```

### D. Resources

**Documentation:**
- [rapidfuzz docs](https://github.com/maxbachmann/RapidFuzz)
- [Scrapy AutoThrottle](https://docs.scrapy.org/en/latest/topics/autothrottle.html)
- [Alembic migrations](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

**Similar Projects:**
- [Tapology](https://www.tapology.com) - Fighter database with locations
- [Sherdog](https://www.sherdog.com) - Fighter profiles

---

**End of Design Document**

*This design is ready for implementation. All major decisions have been made, edge cases considered, and implementation details specified.*
