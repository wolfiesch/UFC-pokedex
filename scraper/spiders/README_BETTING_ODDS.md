# Best Fight Odds Spiders

## Quick Start

### Scrape the Archive (All Organizations)
```bash
scrapy crawl bestfightodds_archive -o data/raw/bfo_events_archive.jsonl
```

### Scrape UFC Events Only
```bash
# Step 1: Get archive
scrapy crawl bestfightodds_archive -o data/raw/bfo_archive.jsonl

# Step 2: Scrape UFC event details
scrapy crawl bestfightodds_event \
  -a input_file="data/raw/bfo_archive.jsonl" \
  -a organization="UFC" \
  -o data/raw/bfo_ufc_odds.jsonl
```

### Scrape Specific Event
```bash
scrapy crawl bestfightodds_event \
  -a event_urls="https://www.bestfightodds.com/events/ufc-vegas-110-3913" \
  -o data/raw/bfo_single_event.jsonl
```

## Available Spiders

### `bestfightodds_archive`
Collects event list from the archive page.

**Output:** Event metadata (name, date, URL, organization)

### `bestfightodds_event`
Collects fight matchups from event pages.

**Output:** Fighter matchups (currently without odds - needs JavaScript support)

## Data Files

- `data/raw/bfo_events_archive.jsonl` - Archive of all events
- `data/raw/bfo_ufc_odds.jsonl` - UFC fight matchups

## Full Documentation

See [`docs/BETTING_ODDS_SCRAPER.md`](../../docs/BETTING_ODDS_SCRAPER.md) for complete documentation including:
- Data schemas
- Limitations and future work
- Alternative data sources
- JavaScript integration guide
