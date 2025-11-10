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
   The command now configures Cloudflare tunnel URLs through environment variable overrides at runtime, keeping your `.env` files untouched. If you choose to work with temporary `.env.dev` files for the backend or frontend, remember to clean them up after you stop the processes.

Refer to `Plans/Initial_Plan.md` for the full project roadmap.

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
