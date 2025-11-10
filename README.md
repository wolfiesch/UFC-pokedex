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

## Container Workflow

Container builds use a multi-stage `uv` pipeline so dependency resolution stays consistent with local development.

### Build the backend image

```bash
docker build -f backend/Dockerfile -t ufc-pokedex-api .
```

The builder stage provisions a reusable virtual environment via `uv`, compiles wheels for all locked dependencies, and then hands a slim runtime layer to Uvicorn.

### Run the full stack with Docker Compose

```bash
docker compose up --build
```

The `api` service exposes `http://localhost:8000`, connects to PostgreSQL via `DATABASE_URL`, and caches responses through Redis using `REDIS_URL`. Health-checked dependencies ensure the FastAPI container starts only after the database is ready.

To rebuild only the backend image after code changes:

```bash
docker compose build api
```

To perform a quick smoke test inside the container:

```bash
docker compose run --rm api uvicorn backend.main:app --help
```

This command exits immediately after verifying the entrypoint wiring while still exercising the packaged dependencies.

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
