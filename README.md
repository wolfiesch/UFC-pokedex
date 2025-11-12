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

### Quick Start (SQLite - No Docker Required)

Perfect for quick testing or when Docker is unavailable:

```bash
# 1. Install dependencies
make bootstrap

# 2. Seed database with sample fighters (creates SQLite database automatically)
make api:seed

# 3. Start backend (in one terminal)
make api:dev

# 4. Start frontend (in another terminal)
make frontend
```

Visit `http://localhost:3000` to see the application.

### Full Setup (PostgreSQL - Recommended for Development)

For production-like development with full dataset support:

```bash
# 1. Install dependencies
make bootstrap

# 2. Copy environment file and update if needed
cp .env.example .env

# 3. Start PostgreSQL + Redis containers
docker-compose up -d

# 4. Run database migrations
make db-upgrade

# 5. Load data (choose one)
make api:seed              # 8 sample fighters
make reload-data           # Full scraped dataset (if you have scraped data)

# 6. Start all services
make dev-local             # Backend + Frontend on localhost
# OR
make dev                   # Backend + Frontend with Cloudflare tunnels
```

### Database Choice

- **SQLite**: Fast setup, no Docker needed, good for UI work and small datasets
- **PostgreSQL**: Production-like, handles large datasets, required for migration testing

See `CLAUDE.md` for detailed comparison and switching instructions.

Refer to `Plans/Initial_Plan.md` for the full project roadmap.

## Container Workflow

Container builds use a multi-stage `uv` pipeline so dependency resolution stays consistent with local development.

```bash
cp .env.example .env
```

Copy the sample environment file before running any container commands and adjust the PostgreSQL credentials as needed.

### Build the backend image

```bash
docker build -f backend/Dockerfile -t ufc-pokedex-api .
```

The builder stage provisions a reusable virtual environment via `uv`, compiles wheels for all locked dependencies, and then hands a slim runtime layer to Uvicorn.

### Run the full stack with Docker Compose

```bash
docker compose up --build
```

The `api` service exposes `http://localhost:8000`, connects to PostgreSQL via `DATABASE_URL`, and caches responses through Redis using `REDIS_URL`. These variables come from the root `.env` file so secrets stay out of version control. Health-checked dependencies ensure the FastAPI container starts only after Redis and the database are ready.

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
