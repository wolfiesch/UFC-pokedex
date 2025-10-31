# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UFC Fighter Pokedex is a full-stack application that scrapes UFC fighter data from UFCStats.com and presents it in a Pokedex-style interface. The project follows a three-tier architecture with a clear data pipeline: Scraper → Database → API → Frontend.

**Tech Stack:**
- Backend: FastAPI + SQLAlchemy (async) + PostgreSQL
- Scraper: Scrapy + BeautifulSoup4
- Frontend: Next.js 14 + React + Tailwind CSS + Zustand
- Package Manager: `uv` (not pip)

## Development Commands

### Setup
```bash
make bootstrap       # Install all dependencies (Python + Node)
make install-dev     # Install only dev dependencies

# Environment setup
cp .env.example .env                    # Create environment file
docker-compose up -d                    # Start PostgreSQL + Redis
make db-upgrade                         # Run database migrations
```

### Running Services
```bash
make dev            # Start backend + frontend together
make api            # Start FastAPI backend only (port 8000)
make frontend       # Start Next.js frontend only (port 3000)
make scraper        # Run Scrapy spider (fighters_list)
```

### Testing & Quality
```bash
make test           # Run all tests (Python + frontend)
pytest              # Run Python tests only
pytest tests/scraper/test_parser.py::test_parse_fighter_list_row  # Single test
cd frontend && npm test                # Frontend tests only

make lint           # Run Ruff + ESLint
make format         # Format code with Ruff + Prettier
```

### Database Operations
```bash
make db-upgrade     # Apply pending migrations
make db-downgrade   # Rollback last migration
make db-reset       # Drop & recreate database (destroys data!)
make load-data      # Load scraped data into database
make load-data-sample  # Load first 10 fighters only
```

### Scraping
```bash
# Sample scrape (single fighter for testing)
make scrape-sample

# Full scraper runs
make scraper                                                   # Get all fighter URLs
make scraper-details                                           # Get all fighter details from list
.venv/bin/scrapy crawl fighter_detail -a fighter_ids=id1,id2  # Specific fighters
.venv/bin/scrapy crawl fighter_detail -a fighter_urls=url1,url2  # Direct URLs

# Note: Use .venv/bin/scrapy (not just scrapy) for direct crawl commands
```

## Architecture

### Data Flow Pipeline

```
UFCStats.com
    ↓ (Scrapy spiders)
data/processed/*.json
    ↓ (load_scraped_data script)
PostgreSQL Database
    ↓ (Repository pattern)
FastAPI Service Layer
    ↓ (REST API)
Next.js Frontend
```

### Backend Structure

The backend uses **dependency injection** and the **repository pattern**:

```
Routes (backend/api/)
  ↓ (FastAPI dependencies)
Services (backend/services/)
  ↓ (orchestrates business logic)
Repositories (backend/db/repositories/)
  ↓ (data access layer)
Database Models (backend/db/models.py)
```

**Key files:**
- `backend/main.py` - FastAPI application entry point
- `backend/api/*.py` - Route handlers (fighters, search, stats)
- `backend/services/fighter_service.py` - Business logic
- `backend/services/search_service.py` - Search service
- `backend/db/repositories.py` - PostgreSQLFighterRepository (database queries)
- `backend/db/models.py` - SQLAlchemy ORM models (Fighter, Fight, fighter_stats)
- `backend/db/connection.py` - Async database session management
- `backend/schemas/fighter.py` - Pydantic response models

**Database schema:**
- `fighters` table: Core fighter info (id, name, nickname, division, height, weight, reach, leg_reach, stance, dob, record)
- `fights` table: Fight history (id, fighter_id FK, opponent_id, opponent_name, event_name, event_date, result, method, round, time, fight_card_url)
- `fighter_stats` table: Key-value stats storage (id, fighter_id FK, category, metric, value) - created but not currently populated

### Scraper Architecture

Two-spider strategy:
1. **FightersListSpider**: Scrapes alphabetical fighter list → `data/processed/fighters_list.jsonl`
2. **FighterDetailSpider**: Scrapes individual fighter pages → `data/processed/fighters/{id}.json`

**Pipeline processing:**
1. ValidationPipeline (priority 100) - Validates with Pydantic models
2. StoragePipeline (priority 200) - Writes to JSON files

**Key files:**
- `scraper/spiders/fighters_list.py` - FightersListSpider (name: "fighters_list")
- `scraper/spiders/fighter_detail.py` - FighterDetailSpider (name: "fighter_detail")
- `scraper/utils/parser.py` - HTML parsing utilities
- `scraper/pipelines/validation.py` - ValidationPipeline
- `scraper/pipelines/storage.py` - StoragePipeline
- `scraper/models/fighter.py` - Pydantic models (FighterListItem, FighterDetail, FightHistoryEntry)

### Frontend Structure

Next.js 14 with App Router + Zustand for state management:

```
app/
├── page.tsx                    # Home: Fighter browser
├── fighters/[id]/page.tsx      # Fighter detail page
└── favorites/page.tsx          # Favorites list

src/
├── components/                 # React components
├── hooks/                      # Custom hooks (useFighters, useFavorites, useSearch)
├── store/favoritesStore.ts     # Zustand store (persisted to localStorage)
└── lib/types.ts                # TypeScript definitions
```

**Data fetching pattern:**
- `useFighters()` hook fetches from `/fighters/` or `/search/` based on filters
- `useFighter(id)` hook fetches from `/fighters/{id}`
- All API calls use `fetch()` with `cache: "no-store"` for real-time data

**State management:**
- Zustand store handles: favorites, searchTerm, stanceFilter
- Persisted to localStorage as `ufc-pokedex-favorites`

## Important Patterns & Conventions

### Python Package Management
- **Always use `uv` instead of `pip`**
- Dependencies are defined in `pyproject.toml` (not requirements.txt)
- `uv sync` installs dependencies from pyproject.toml
- `uv sync --all-extras` includes dev dependencies

### Database Migrations
- Use Alembic for schema changes
- Migration files in `backend/db/migrations/versions/`
- Always run `.venv/bin/python -m alembic` (not `alembic` directly)
- Test migrations: upgrade → downgrade → upgrade

### Async Everywhere (Backend)
- All database operations use `AsyncSession`
- All FastAPI routes are `async def`
- Repository methods are async
- Use `await` for database queries

### Code Quality
- Ruff for linting + formatting (configured in pyproject.toml)
- mypy for type checking
- Target Python 3.11+
- Line length: 100 characters

## Common Development Tasks

### Adding a New API Endpoint
1. Define route in `backend/api/` (e.g., `fighters.py`)
2. Add business logic to appropriate service in `backend/services/` (e.g., `fighter_service.py`)
3. Add database query to `backend/db/repositories.py` (PostgreSQLFighterRepository) if needed
4. Use dependency injection: `service = Depends(get_fighter_service)` or similar
5. Define response models in `backend/schemas/fighter.py` for type safety
6. Register router in `backend/main.py` if creating a new module

### Adding a New Scraper Field
1. Update Pydantic models in `scraper/models/fighter.py` (FighterListItem or FighterDetail)
2. Update parser in `scraper/utils/parser.py` (parse_fighter_list_row or parse_fighter_detail_page)
3. Update database model in `backend/db/models.py` (Fighter or Fight class)
4. Update repository in `backend/db/repositories.py` (mapping in list_fighters or get_fighter)
5. Create Alembic migration: `.venv/bin/python -m alembic revision -m "add_field_name"`
6. Run migration: `make db-upgrade`
7. Update API response models in `backend/schemas/fighter.py` if needed

### Creating a Database Migration
```bash
# Generate migration file
.venv/bin/python -m alembic revision -m "description_of_change"

# Edit the generated file in backend/db/migrations/versions/
# Implement upgrade() and downgrade() functions

# Apply migration
make db-upgrade

# Test rollback
make db-downgrade
```

### Running Python Scripts and Commands
Always use `.venv/bin/python` or `.venv/bin/scrapy` when running commands directly:

```bash
# Correct
.venv/bin/python -m alembic upgrade head
.venv/bin/scrapy crawl fighters_list
.venv/bin/python -m scripts.load_scraped_data

# Incorrect (will use system Python/scrapy, not project virtual environment)
alembic upgrade head
scrapy crawl fighters_list
python -m scripts.load_scraped_data
```

Or use the Makefile commands which handle this automatically:
```bash
make db-upgrade    # Uses .venv/bin/python internally
make scraper       # Uses .venv/bin/scrapy internally
```

### Debugging Tips
- Backend logs: Check FastAPI uvicorn output for route errors
- Database queries: Enable SQLAlchemy echo in `backend/db/connection.py`
- Scraper logs: Scrapy outputs to console, check `data/processed/` for output files
- Frontend: Check browser console + Next.js terminal for errors
- Search endpoint: The `q` parameter is required (use `/search/?q=fighter_name`)

## Known TODOs & Limitations

- **Backend**: Fight history stats are not populated from `fighter_stats` table (fields exist but unused)
- **Backend**: Age calculation from DOB not implemented
- **Scraper**: No scheduled updates (manual runs only)
- **Frontend**: No fighter images (UFCStats doesn't provide them)
- **Frontend**: No pagination for large fighter lists
- **Database**: `fighter_stats` table is created but not populated by scraper
- **Cache**: Redis is configured in docker-compose but not integrated into backend

## Environment Variables

Required in `.env`:
```
DATABASE_URL=postgresql+psycopg://ufc_pokedex:ufc_pokedex@localhost:5432/ufc_pokedex
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Optional (with defaults):
```
SCRAPER_USER_AGENT=UFC-Pokedex-Scraper/0.1 (+https://github.com/example/ufc-pokedex)
SCRAPER_DELAY_SECONDS=1.5
SCRAPER_CONCURRENT_REQUESTS=4
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
```

**Note:**
- Use `@localhost` for local development when running backend on host machine
- Use `@db` when running backend in Docker container
- Copy `.env.example` to `.env` to get started
