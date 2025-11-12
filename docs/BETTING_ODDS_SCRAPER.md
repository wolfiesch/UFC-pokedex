# UFC Betting Odds Scraper

## Overview

This document describes the custom scrapers built to collect historical UFC betting odds data from **Best Fight Odds** (bestfightodds.com), which maintains one of the most comprehensive archives of MMA betting odds dating back to 2007.

## Data Source

**Best Fight Odds** provides:
- Historical odds from 12+ major sportsbooks
- Coverage from 2007 to present
- Moneyline odds for fight winners
- Prop bets (method of victory, rounds, etc.)
- Opening and closing lines
- Line movement tracking

## Architecture

The scraping system consists of two spiders:

### 1. Archive Spider (`bestfightodds_archive`)
Scrapes the archive page to collect all available UFC events.

**Output:** List of events with metadata
**Data File:** `data/raw/bfo_events_archive.jsonl`

### 2. Event Detail Spider (`bestfightodds_event`)
Scrapes individual event pages to extract fight matchups and betting odds.

**Output:** Fight matchups with odds data
**Data File:** `data/raw/bfo_events_odds.jsonl`

## Usage

### Step 1: Scrape the Events Archive

```bash
# Scrape all recent events from the archive
scrapy crawl bestfightodds_archive -o data/raw/bfo_events_archive.jsonl

# Check how many events were scraped
wc -l data/raw/bfo_events_archive.jsonl

# View UFC events only
cat data/raw/bfo_events_archive.jsonl | jq -r 'select(.organization == "UFC") | "\(.event_date) - \(.event_title)"'
```

### Step 2: Scrape Event Details (Matchups & Odds)

```bash
# Scrape all UFC events from the archive file
scrapy crawl bestfightodds_event -a input_file="data/raw/bfo_events_archive.jsonl" -a organization="UFC" -o data/raw/bfo_ufc_odds.jsonl

# Or scrape a specific event by URL
scrapy crawl bestfightodds_event -a event_urls="https://www.bestfightodds.com/events/ufc-vegas-110-3913" -o data/raw/bfo_single_event.jsonl

# Scrape multiple specific events
scrapy crawl bestfightodds_event -a event_urls="https://www.bestfightodds.com/events/ufc-322-3924,https://www.bestfightodds.com/events/ufc-vegas-111-3917" -o data/raw/bfo_multiple_events.jsonl
```

## Data Schema

### Archive Spider Output

```json
{
  "event_id": "ufc-vegas-111-3917",
  "event_numeric_id": "3917",
  "event_title": "UFC Vegas 111",
  "event_date": "2025-11-09",
  "event_url": "https://www.bestfightodds.com/events/ufc-vegas-111-3917",
  "organization": "UFC",
  "scraped_at": "2025-11-12T15:14:32.404093"
}
```

**Fields:**
- `event_id`: Unique slug identifier (e.g., "ufc-vegas-111-3917")
- `event_numeric_id`: Numeric ID used by Best Fight Odds
- `event_title`: Full event name
- `event_date`: ISO date format (YYYY-MM-DD)
- `event_url`: Full URL to the event detail page
- `organization`: Detected organization (UFC, Bellator, ONE, etc.)
- `scraped_at`: UTC timestamp when scraped

### Event Detail Spider Output

```json
{
  "event_id": "ufc-vegas-110-3913",
  "event_title": "UFC Vegas 110",
  "event_date": "November 1st",
  "event_url": "https://www.bestfightodds.com/events/ufc-vegas-110-3913",
  "matchup_id": "40336",
  "fighter_1": {
    "name": "David Onama",
    "url": "https://www.bestfightodds.com/fighters/David-Onama-10808"
  },
  "fighter_2": {
    "name": "Steve Garcia",
    "url": "https://www.bestfightodds.com/fighters/Steve-Garcia-2576"
  },
  "odds": {},
  "scraped_at": "2025-11-12T15:14:52.970283"
}
```

**Fields:**
- `event_id`: References the event from the archive
- `event_title`: Event name
- `event_date`: Event date as displayed on the page
- `event_url`: URL to the event detail page
- `matchup_id`: Unique identifier for the fight matchup
- `fighter_1`: First fighter's name and profile URL
- `fighter_2`: Second fighter's name and profile URL
- `odds`: Dictionary of betting odds (currently empty, requires JavaScript)
- `scraped_at`: UTC timestamp

## Limitations & Future Work

### Current Limitations

1. **JavaScript-Rendered Odds Data**
   - The actual betting odds are loaded dynamically via JavaScript
   - Current implementation only captures fighter matchups
   - Odds data requires browser automation (Selenium/Playwright) or API reverse-engineering

2. **Archive Pagination**
   - Currently only scrapes the first page of the archive
   - Need to implement pagination to access historical events beyond recent ones

3. **Rate Limiting**
   - Configured with 2-second delays to be respectful
   - May need adjustments for large-scale scraping

### Recommended Next Steps

#### Option 1: Add Playwright/Selenium Support
```python
# Use Scrapy-Playwright to render JavaScript
# Install: pip install scrapy-playwright

# Update settings.py:
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

# In spider:
yield scrapy.Request(
    url=event_url,
    callback=self.parse,
    meta={"playwright": True, "playwright_include_page": True}
)
```

#### Option 2: Reverse-Engineer the API
Best Fight Odds likely has an internal API that loads odds data. Inspect network traffic in browser DevTools to find:
- API endpoints
- Request parameters
- Authentication (if any)

#### Option 3: Use Pre-Existing Datasets
- GitHub: jansen88/ufc-data (2014-2023 betting odds)
- Kaggle: UFC Fights 2010-2020 with Betting Odds
- The Odds API (paid service, from mid-2020)

## Example Workflows

### Scrape Recent UFC Events
```bash
# 1. Get archive
scrapy crawl bestfightodds_archive -o data/raw/bfo_archive.jsonl

# 2. Filter UFC events only and scrape details
scrapy crawl bestfightodds_event -a input_file="data/raw/bfo_archive.jsonl" -a organization="UFC" -o data/raw/bfo_ufc_fights.jsonl

# 3. Analyze the data
cat data/raw/bfo_ufc_fights.jsonl | jq -r '"\(.fighter_1.name) vs \(.fighter_2.name) - \(.event_title)"'
```

### Compare Fighters Across Events
```bash
# Find all fights involving a specific fighter
cat data/raw/bfo_ufc_fights.jsonl | jq -r 'select(.fighter_1.name == "Israel Adesanya" or .fighter_2.name == "Israel Adesanya") | "\(.event_date) - \(.fighter_1.name) vs \(.fighter_2.name)"'
```

## Configuration

Both spiders can be configured via environment variables or scrapy settings:

```python
# scraper/config.py
SCRAPER_USER_AGENT = "UFC-Pokedex-Scraper/0.1 (+local)"
SCRAPER_DELAY_SECONDS = 2.0
SCRAPER_CONCURRENT_REQUESTS = 2
```

## Ethical Considerations

- **Respect robots.txt**: Both spiders honor `ROBOTSTXT_OBEY = True`
- **Rate limiting**: 2-second delays between requests
- **User agent**: Properly identified user agent string
- **Caching**: HTTP caching enabled to avoid unnecessary requests
- **Purpose**: Educational and research purposes only

## Spider Implementation Files

- `scraper/spiders/bestfightodds_archive.py` - Archive scraper
- `scraper/spiders/bestfightodds_event.py` - Event detail scraper
- `docs/BETTING_ODDS_SCRAPER.md` - This documentation

## Alternative Data Sources

If Best Fight Odds becomes unavailable or additional data is needed:

1. **OddsPortal** - Comprehensive odds archive (has anti-scraping measures)
2. **The Odds API** - Paid API service (from mid-2020, JSON format)
3. **Kaggle Datasets** - Pre-scraped historical data
4. **GitHub Repositories** - Community-maintained datasets
5. **betmma.tips** - Alternative source (used by some GitHub projects)

## Support

For issues or questions:
- Check the Scrapy logs for detailed error messages
- Enable debug logging: `scrapy crawl bestfightodds_archive --loglevel=DEBUG`
- Review Best Fight Odds' structure if scraping fails (site may have changed)

---

**Last Updated:** November 12, 2025
**Status:** ✅ Archive scraper functional | ⚠️ Event detail scraper needs JavaScript support for odds data
