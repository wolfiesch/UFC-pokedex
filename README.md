# UFC Fighter Pokedex

A full-stack project that scrapes fighter data from [UFCStats](http://ufcstats.com) and serves an interactive Pokedex-style experience.

## Structure

- `scraper/` – Scrapy project + BeautifulSoup utilities.
- `backend/` – FastAPI service exposing fighter data.
- `frontend/` – Next.js 14 application with Tailwind styling.
- `docs/` – Research and project documentation.
- `scripts/` – Operational scripts (scrape, seed).
- `data/` – Local data cache (ignored from version control).

## Getting Started

1. Follow `docs/setup/environment_setup.md`.
2. Copy `.env.example` to `.env` and update secrets.
3. Bootstrap databases and dependencies:
   ```bash
   make bootstrap
   ```
4. Run all services locally:
   ```bash
   make dev
   ```

Refer to `Plans/Initial_Plan.md` for the full project roadmap.

## API Reference

The FastAPI service exposes typed responses designed for the Stats Hub and fighter detail views.

### `GET /fighters/`

Paginated fighter index supporting `limit` and `offset` query parameters. Returns:

```json
{
  "fighters": [
    {
      "fighter_id": "alpha-1",
      "detail_url": "http://ufcstats.com/fighter-details/alpha-1",
      "name": "Alpha One",
      "nickname": "The First",
      "division": "Lightweight",
      "height": "5' 9\"",
      "weight": "155 lbs.",
      "reach": "72\"",
      "stance": "Orthodox",
      "dob": "1990-01-01"
    }
  ],
  "total": 1200,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

### `GET /fighters/{fighter_id}`

Returns a `FighterDetail` payload including grappling/striking aggregates and fight history items.

### `GET /fighters/random`

Provides a single random fighter (useful for "Surprise Me" UI interactions).

### `GET /search/`

Filters fighters by `q` (substring match) and optional `stance` query parameters. Response mirrors the
list endpoint's `FighterListItem` objects.

### `GET /stats/summary`

Aggregates counts and metrics for Stats Hub visualizations. Current fields:

```json
{
  "fighters_indexed": 1200.0,
  "best_striking_accuracy": 0.64,
  "recent_trend_delta": 0.3
}
```

Values are raw ratios; the frontend converts them into percentages or per-minute rates.

## Refreshing Data

Scraped fighters only receive division and other enriched fields after the detail JSON files are loaded into the database.

1. (Optional) Refresh raw scrape artifacts:
   ```bash
   make scraper
   make scraper-details
   ```
2. Load the list and detail data into PostgreSQL:
   ```bash
   make reload-data
   ```

You can also call the underlying targets directly:

- `make load-data` ingests the fighter list JSONL only.
- `make load-data-details` ingests detail JSON files without reloading the list data.
