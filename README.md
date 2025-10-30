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

