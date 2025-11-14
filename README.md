# UFC Fighter Pokedex

A full-stack project that scrapes fighter data from [UFCStats](http://ufcstats.com) and serves an interactive Pokedex-style experience.

## Structure

- `scraper/` – Scrapy project + BeautifulSoup utilities.
- `backend/` – FastAPI service exposing fighter data.
- `frontend/` – Next.js 14 application with Tailwind styling.
- `docs/` – Research notes, runbooks, plans, and AI-assistant guides (see `docs/README.md`).
- `scripts/` – Operational scripts (scrape, seed).
- `tests/` – Automated suites plus `tests/manual/` for exploratory QA scripts.
- `data/` – Local cache and archived payloads (`data/backups/legacy/` stores SQL dumps; see `docs/runbooks/operations/backups.md`).

## Getting Started

### Quick Start (PostgreSQL)

PostgreSQL backs every environment. Use Docker Compose for a fast local setup:

```bash
# 1. Install dependencies
make bootstrap

# 2. Copy environment file and configure DATABASE_URL (PostgreSQL)
cp .env.example .env

# 3. Start PostgreSQL + Redis containers
docker-compose up -d

# 4. Run database migrations
make db-upgrade

# 5. Load data (choose one)
make api:seed              # 8 sample fighters
make reload-data           # Full scraped dataset (if you have scraped data)

# 6. Start all services with smart auto-detection
make dev                   # Auto-detects: Cloudflare → ngrok → localhost
```

### Database Configuration

Accepted `DATABASE_URL` prefixes for PostgreSQL are:

- `postgresql+psycopg://` (preferred async driver)
- `postgresql://` (auto-upgraded to `postgresql+psycopg://`)
- `postgres://` (legacy alias that is auto-upgraded to `postgresql+psycopg://`)

See `docs/ai-assistants/CLAUDE.md` for detailed PostgreSQL setup instructions.

Refer to `docs/plans/archive/Initial_Plan.md` for the full project roadmap.

### Development Modes

The `make dev` command automatically detects the best available tunneling option and configures your environment accordingly:

**🌐 Cloudflare Tunnel (Best)**
- Used if: `cloudflared` is installed AND `~/.cloudflared/config.yml` exists
- URL: https://ufc.wolfgangschoenberger.com (stable, permanent)
- Setup: One-time Cloudflare tunnel configuration required
- Best for: Your personal development workflow, production-like testing

**🚇 ngrok Tunnel (Fallback)**
- Used if: `ngrok` is installed (Cloudflare not configured)
- URL: Random HTTPS URL (changes on each restart)
- Setup: `brew install ngrok` + `ngrok config check`
- Best for: Quick testing, sharing with others, new developers

**🏠 Localhost Only (Ultimate Fallback)**
- Used if: No tunnel tools are available
- URL: http://localhost:3000
- Setup: None required (always works)
- Best for: Offline development, CI/CD, minimal setup

All modes use the same architecture: Frontend (port 3000) → Next.js API proxy → Backend (port 8000).

**Manual Mode Selection:**
```bash
make dev-cloudflare  # Force Cloudflare tunnel
make dev-ngrok       # Force ngrok tunnel
make dev-local       # Force localhost only
```

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

## Manual Smoke Tests

Quick exploratory scripts now live under `tests/manual/` (documented in `tests/manual/README.md`). They are excluded from the default `pytest` run; execute them directly (e.g., `PYTHONPATH=. uv run python tests/manual/test_comprehensive_webapp.py`) when you need to reproduce end-to-end flows outside the automated suites.
