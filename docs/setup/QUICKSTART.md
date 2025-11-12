# UFC Pokedex - Quick Start Guide

## First Time Setup

```bash
# 1. Install dependencies
make bootstrap

# 2. Setup environment
cp .env.example .env

# 3. Start database
docker-compose up -d

# 4. Run migrations
make db-upgrade

# 5. Load fighter data (if you have scraped data)
make load-data
```

## Daily Development

### Start Everything (Localhost Only)
```bash
make dev-local
```

This starts:
- ✅ Backend on `http://localhost:8000`
- ✅ Frontend on `http://localhost:3000`
- ✅ Logs streaming to terminal

**To stop:** Press `Ctrl+C`, then run:
```bash
make stop
```

### Start with Cloudflare Tunnels (Public URLs)
```bash
make dev
```

This starts everything PLUS Cloudflare Tunnels:
- ✅ Backend on `http://localhost:8000` AND `https://api.ufc.wolfgangschoenberger.com`
- ✅ Frontend on `http://localhost:3000` AND `https://ufc.wolfgangschoenberger.com`

**Note:** Requires one-time tunnel setup first:
```bash
bash scripts/setup_tunnel.sh
```

## Individual Services

```bash
# Backend only
make api

# Frontend only
make frontend

# Stop everything
make stop
```

## Database Operations

```bash
# Apply migrations
make db-upgrade

# Rollback migration
make db-downgrade

# Reset database (⚠️ destroys all data)
make db-reset

# Load scraped data
make load-data
```

## Scraping

```bash
# Get fighter list
make scraper

# Get fighter details
make scraper-details

# Sample scrape (for testing)
make scrape-sample
```

## Testing

```bash
# Run all tests
make test

# Run linters
make lint

# Format code
make format
```

## Troubleshooting

### Fighters not loading?

1. **Check services are running:**
   ```bash
   lsof -i :3000  # Frontend
   lsof -i :8000  # Backend
   ```

2. **Check logs:**
   ```bash
   tail -f /tmp/backend.log
   tail -f /tmp/frontend.log
   ```

3. **Restart services:**
   ```bash
   make stop
   make dev-local
   ```

### Port already in use?

```bash
# Kill processes on ports 3000 and 8000
make stop
```

### Database connection error?

```bash
# Make sure Docker is running
docker-compose ps

# Restart database
docker-compose down
docker-compose up -d
```

## Environment Files

- **`.env`** - Backend configuration (CORS, database URL)
- **`frontend/.env.local`** - Frontend API URL (localhost by default)
- **`frontend/.env.tunnel`** - Frontend API URL for Cloudflare Tunnel
- **Optional:** `.env.dev` and `frontend/.env.dev` - Temporary overrides loaded via `dotenv`

**Important:** `make dev` now exports tunnel URLs as environment variables at runtime instead of editing your tracked `.env` files. If you prefer file-based overrides, create temporary `.env.dev` and `frontend/.env.dev` copies. You will need to modify your application's startup logic to load these files. Remember to delete those files after shutting everything down to avoid leaking tunnel-specific values into source control.

## Quick Commands Reference

| Command | Description |
|---------|-------------|
| `make dev-local` | Start backend + frontend (localhost only) ⭐ |
| `make dev` | Start everything with Cloudflare Tunnels |
| `make stop` | Stop all services |
| `make api` | Backend only |
| `make frontend` | Frontend only |
| `make test` | Run tests |
| `make lint` | Check code quality |
| `make db-upgrade` | Apply database migrations |
| `make load-data` | Load scraped data into database |

## URLs

**Local Development:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Backend API Docs: http://localhost:8000/docs

**Public (via Cloudflare Tunnel):**
- Frontend: https://ufc.wolfgangschoenberger.com
- Backend: https://api.ufc.wolfgangschoenberger.com

## Need More Help?

- Full documentation: See `../ai-assistants/CLAUDE.md`
- Tunnel setup: See `TUNNEL_SETUP.md`
- Check DNS propagation: `bash scripts/check_dns_propagation.sh`
