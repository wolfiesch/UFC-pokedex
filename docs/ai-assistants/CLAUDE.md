# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UFC Fighter Pokedex is a full-stack application that scrapes UFC fighter data from UFCStats.com and presents it in a Pokedex-style interface. The project follows a three-tier architecture with a clear data pipeline: Scraper → Database → API → Frontend.

**Tech Stack:**
- Backend: FastAPI + SQLAlchemy (async) + PostgreSQL
- Scraper: Scrapy + BeautifulSoup4
- Frontend: Next.js 14 + React + Tailwind CSS + Zustand
- Package Manager: `uv` (not pip)
- Testing: Playwright MCP for E2E browser automation

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
# Development modes (choose one)
make dev-local      # Localhost only (recommended for local dev)
make dev-tunnel     # Public HTTPS via Cloudflare tunnel
make dev            # Alias for dev-tunnel

# Individual services
make api            # Start FastAPI backend only (port 8000)
make frontend       # Start Next.js frontend only (port 3000)

# Utility commands
make stop           # Stop all running services (backend, frontend, tunnels)
make dev-clean      # Clean frontend caches and restart (fixes webpack cache issues)
```

#### Development Mode Comparison

| Command | Use Case | Public Access | SSL/HTTPS | Auto-Config |
|---------|----------|---------------|-----------|-------------|
| `make dev-local` | Local development | ❌ No | ❌ No | ✅ Yes |
| `make dev-tunnel` | Share with others / test on phone | ✅ Yes | ✅ Yes | ✅ Yes |

**Recommended for local development:** Use `make dev-local` - it keeps everything on localhost and automatically configures `frontend/.env.local`.

**For public access:** Use `make dev-tunnel` - it starts a Cloudflare tunnel and auto-configures the frontend to use the tunnel's proxy pattern (see Tunnel Troubleshooting below).

**Troubleshooting dev build crashes:** If you encounter webpack cache issues, MODULE_NOT_FOUND errors, or chunk 404s, run `make dev-clean` to clear all frontend build caches and restart cleanly.

### Cloudflare Tunnel Troubleshooting

#### Common Issue: "Network request failed" or SSL errors

**Symptoms:**
```
ERR_SSL_VERSION_OR_CIPHER_MISMATCH
ERR_NAME_NOT_RESOLVED
Mixed Content warnings
```

**Root Cause:** Cloudflare's free tunnel doesn't support second-level subdomains with valid SSL certificates.

- ✅ Works: `random-id.trycloudflare.com` (covered by wildcard cert)
- ❌ Fails: `api.random-id.trycloudflare.com` (not covered)

**Solution:** The project uses **Next.js as a proxy** to route all requests through a single tunnel:

```
Browser → https://tunnel-url.com/api/* → Next.js (port 3000) → Backend (port 8000)
```

This is handled automatically by `make dev-tunnel`, which:
1. Starts Cloudflare tunnel on port 3000
2. Configures `frontend/.env.local` with `/api` proxy URLs
3. Next.js rewrites `/api/*` → `http://localhost:8000/*`

**If you encounter tunnel issues:**
```bash
# 1. Stop everything
make stop

# 2. Restart with tunnel (regenerates correct config)
make dev-tunnel

# 3. Verify the config
cat frontend/.env.local
# Should show:
#   NEXT_PUBLIC_API_BASE_URL=https://random-id.trycloudflare.com/api
#   NEXT_API_REWRITE_BASE_URL=http://localhost:8000
```

**Never manually edit `.env.local`!** It's auto-generated and git-ignored. Always use `make` commands to switch modes.

**For detailed tunnel documentation:** See [docs/TUNNEL.md](../../docs/TUNNEL.md)

## Database Setup (PostgreSQL only)

PostgreSQL is now the single supported database engine for the project. Every local, staging, and production environment must target a running PostgreSQL instance (Docker Compose is the recommended way to satisfy the dependency).

### Required services

- Run `docker compose up -d` to provision PostgreSQL and Redis before starting any Python processes.
- Copy `.env.example` to `.env` and fill in `DATABASE_URL` with a PostgreSQL connection string (for example `postgresql+psycopg://ufc_pokedex:ufc_pokedex@localhost:5432/ufc_pokedex`).
- Use `make ensure-docker` if you need a quick health check/auto-start for the Compose services.

### Initializing the schema

```bash
make bootstrap        # Install Python + Node dependencies
docker compose up -d  # Launch PostgreSQL + Redis
make db-upgrade       # Apply Alembic migrations
```

### Working with data

```bash
make api:seed         # Load lightweight sample fighters
make reload-data      # Load scraped list + detail JSONL payloads
make load-data        # Load list-only dataset
make load-data-details  # Load detail-only dataset
```

### Development entry points

- `make dev-local` and `make dev-tunnel` both expect PostgreSQL to be running; they will fail fast if `DATABASE_URL` is missing or the server is unavailable.
- `make api-dev` now shells into the same Postgres-backed environment as `make api` while keeping auto-reload enabled. It calls `ensure-docker` first so Compose services come online automatically.
- There is no SQLite fallback—the backend will log a clear error if `DATABASE_URL` points anywhere other than PostgreSQL.

### Troubleshooting

- Verify the container: `docker compose ps` should show `postgres` as healthy before starting FastAPI.
- Inspect migrations: `alembic history --verbose` lists the revisions that `make db-upgrade` will apply.
- Reset the database if needed: `make db-reset` drops and recreates the schema using PostgreSQL.
- Connection errors typically indicate a missing `.env` file or an offline Compose stack; re-run `make ensure-docker` and confirm credentials.

### Cloudflare Tunnel (Public Access)

The project is configured to use Cloudflare Tunnel for public access to your local development environment.

**Public URLs:**
- Frontend: `https://ufc.wolfgangschoenberger.com`
- Backend API: `https://api.ufc.wolfgangschoenberger.com`

**One-time setup** (run this once):
```bash
bash scripts/setup_tunnel.sh
```

This will:
1. Authenticate with Cloudflare (opens browser)
2. Create a tunnel named `ufc-pokedex`
3. Set up DNS routes for your subdomains
4. Generate config file at `~/.cloudflared/config.yml`

**Starting tunnels:**
The tunnel automatically starts when you run `make dev`. No separate command needed!

**Manual tunnel commands** (if needed):
```bash
cloudflared tunnel run ufc-pokedex     # Start tunnel manually
make tunnel-stop                        # Stop all tunnels
cloudflared tunnel list                 # List all tunnels
cloudflared tunnel info ufc-pokedex     # Get tunnel details
```

**Troubleshooting:**
- Check tunnel logs: `tail -f /tmp/tunnel.log`
- Verify DNS: `nslookup ufc.wolfgangschoenberger.com`
- Test connectivity: `curl https://api.ufc.wolfgangschoenberger.com/health`
- Re-run setup if DNS routes are missing: `bash scripts/setup_tunnel.sh`

### Railway Deployment (Production Backend)

Deploy your FastAPI backend to Railway for production hosting with PostgreSQL and Redis.

**Quick Deploy:**
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login to Railway
railway login

# Initialize project (first time only)
railway init

# Add PostgreSQL plugin
railway add --plugin postgresql

# Add Redis plugin (optional)
railway add --plugin redis

# Deploy
railway up
```

**Configuration Files:**
- `railway.json` - Railway service configuration
- `nixpacks.toml` - Nixpacks build configuration
- `.railway-ignore` - Files to exclude from deployment
- `.env.railway` - Environment variables template

**Required Environment Variables:**
Railway will auto-configure `DATABASE_URL` and `REDIS_URL` when you add the plugins. You need to manually set:

```bash
# Set via Railway dashboard or CLI
railway variables set CORS_ALLOW_ORIGINS=https://your-frontend-domain.com
railway variables set LOG_LEVEL=INFO
```

**Railway MCP Server:**
Control Railway deployments through Claude Code using the Railway MCP server (configured in `.claude/mcp.json`):

```bash
# Get your Railway API token
# Visit: https://railway.app/account/tokens

# Set token in environment
export RAILWAY_API_TOKEN=your-token-here
```

**MCP Commands:**
```
"Show me my Railway projects"
"Deploy the backend to production"
"Get logs from my API service"
"List all environment variables"
"Create a new Railway environment for staging"
```

**Deployment Workflow:**
1. Push code to GitHub
2. Railway auto-deploys on push to main branch (configure in Railway dashboard)
3. Or deploy manually: `railway up`
4. Check health: `curl https://your-railway-domain.railway.app/health`

**Database Migrations on Railway:**
Railway will automatically run migrations if you configure a deploy command:
```bash
railway run uv run alembic upgrade head
```

**Monitoring:**
```bash
railway logs                    # View recent logs
railway status                  # Check service status
railway open                    # Open Railway dashboard
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

### E2E Testing with Playwright MCP
Playwright MCP is configured for browser automation and E2E testing. Available capabilities:

**Navigation & Inspection:**
- Navigate to URLs and capture page state
- Take screenshots (viewport or full page)
- Capture accessibility snapshots (structured YAML of page content)
- Execute JavaScript to inspect/manipulate page
- Monitor network requests and console messages

**User Interactions:**
- Click, hover, type, drag-and-drop
- Fill forms and select dropdowns
- Upload files and handle dialogs
- Press keyboard keys

**Session Management:**
- Create, switch, and close tabs
- Wait for elements or time delays
- Resize browser window

Screenshots are saved to `.playwright-mcp/` directory.

### Schema Generation & Type Safety

The project uses **OpenAPI → TypeScript code generation** to maintain a single source of truth for API contracts. Backend Pydantic schemas are automatically converted to TypeScript types.

**Commands:**
```bash
make types-generate     # Generate TypeScript types from OpenAPI (requires backend running)
```

**Automatic Generation:**
- Types are **auto-generated** when you run `make dev` or `make dev-local`
- No manual action needed during normal development

**Architecture:**
```
Backend Pydantic Models (backend/schemas/)
    ↓
FastAPI Auto-generates OpenAPI Schema (/openapi.json)
    ↓
openapi-typescript Generator (npm package)
    ↓
TypeScript Types (frontend/src/lib/generated/api-schema.ts)
    ↓
Type-Safe API Client (frontend/src/lib/api-client.ts)
```

**Usage:**
```ts
// Import the type-safe client
import client from '@/lib/api-client';

// All endpoints, parameters, and responses are fully typed!
const { data, error } = await client.GET('/fighters/', {
  params: {
    query: { limit: 20, offset: 0 }
  }
});

if (error) {
  // Handle error (typed!)
  console.error(error);
  return;
}

// data.fighters is fully typed - autocomplete works!
console.log(data.fighters);
```

**Benefits:**
- ✅ Single source of truth (Backend Pydantic schemas)
- ✅ Zero manual type duplication
- ✅ Compile-time validation of API calls
- ✅ Full IDE autocomplete for all endpoints
- ✅ Catches API contract violations before runtime

**Migration:**
See `frontend/MIGRATION_GUIDE.md` for examples of migrating from old `api.ts` to the new type-safe client.

**Troubleshooting:**
- **Types are stale**: Run `make types-generate` to regenerate
- **Backend not running**: Start with `make api-dev` first
- **Generated file location**: `frontend/src/lib/generated/api-schema.ts` (gitignored)

**Key Files:**
- `frontend/src/lib/api-client.ts` - Type-safe API client wrapper
- `frontend/src/lib/generated/api-schema.ts` - Auto-generated types (DO NOT EDIT)
- `backend/schemas/*.py` - Source of truth for API contracts
- `frontend/MIGRATION_GUIDE.md` - Migration examples and patterns

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
    ↓ (Cloudflare Tunnel - optional)
Public Internet (ufc.wolfgangschoenberger.com)
```

### Cloudflare Tunnel Architecture

When running `make dev`, the application is exposed via Cloudflare Tunnel:

```
Internet
    ↓ (HTTPS)
Cloudflare Global Network
    ↓ (Cloudflare Tunnel)
Local Machine (localhost)
    ├─ Port 3000 → ufc.wolfgangschoenberger.com (Frontend)
    └─ Port 8000 → api.ufc.wolfgangschoenberger.com (Backend)
```

**Key files:**
- `scripts/setup_tunnel.sh` - One-time tunnel setup script
- `scripts/start_tunnels.sh` - Tunnel startup script (called by `make dev`)
- `~/.cloudflared/config.yml` - Tunnel configuration (created by setup script)
- `.cloudflared/config.template.yml` - Template for reference

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
- E2E testing: Use Playwright MCP tools to inspect page state, capture screenshots, and monitor network/console

## Known TODOs & Limitations

- **Backend**: Fight history stats are not populated from `fighter_stats` table (fields exist but unused)
- **Backend**: Age calculation from DOB not implemented
- **Scraper**: No scheduled updates (manual runs only)
- **Frontend**: No fighter images (UFCStats doesn't provide them)
- **Frontend**: No pagination for large fighter lists
- **Database**: `fighter_stats` table is created but not populated by scraper
- **Cache**: Redis is integrated for caching but optional (backend gracefully degrades if Redis is unavailable)

## Environment Variables

**Frontend (required):**
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

**Backend (configure via `.env`):**
```
# Database (required - PostgreSQL only)
DATABASE_URL=postgresql+psycopg://ufc_pokedex:ufc_pokedex@localhost:5432/ufc_pokedex

# Redis cache (optional - gracefully degrades if unavailable)
REDIS_URL=redis://localhost:6379/0

# API server (optional - has defaults)
API_HOST=0.0.0.0
API_PORT=8000
CORS_ALLOW_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO

# Scraper (optional - has defaults)
SCRAPER_USER_AGENT=UFC-Pokedex-Scraper/0.1 (+https://github.com/example/ufc-pokedex)
SCRAPER_DELAY_SECONDS=1.5
SCRAPER_CONCURRENT_REQUESTS=4
```

**Note on Redis:**
- Redis is used for caching API responses to improve performance
- If Redis connection fails, the backend will log a warning and continue without caching
- For local development: `REDIS_URL=redis://localhost:6379/0`
- For Docker-based backend: `REDIS_URL=redis://redis:6379/0`

**Cloudflare Tunnel URLs** (auto-configured by `make dev`):
```
# Frontend (automatically set in frontend/.env.local by make dev)
NEXT_PUBLIC_API_BASE_URL=https://api.ufc.wolfgangschoenberger.com

# Backend (automatically set in .env by make dev)
CORS_ALLOW_ORIGINS=https://ufc.wolfgangschoenberger.com
```

**MCP Servers** (optional - for Claude Code automation):
```bash
# Railway MCP Server (for deployment automation)
export RAILWAY_API_TOKEN=your-railway-token

# Get token from: https://railway.app/account/tokens
```

**MCP Configuration:**
MCP servers are configured in `.claude/mcp.json` (project-level):
- **Vercel MCP**: Deployed via HTTP at `https://mcp.vercel.com/` (OAuth authentication)
- **Railway MCP**: Installed via NPX with `RAILWAY_API_TOKEN` for authentication

**Note:**
- Use `@localhost` for local development when running backend on host machine
- Use `@db` when running backend in Docker container
- Copy `.env.example` to `.env` to get started
- `make dev` automatically configures tunnel URLs in `.env` and `frontend/.env.local`
- MCP servers enable conversational deployment and monitoring through Claude Code
