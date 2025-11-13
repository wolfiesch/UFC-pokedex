# Quick Start Guide

## First Time Setup

```bash
# 1. Install dependencies
make bootstrap

# 2. Start database
docker compose up -d

# 3. Run migrations
make db-upgrade

# 4. Load sample data (optional)
make load-data-sample
```

## Daily Development

### Choose Your Mode

```bash
# Local development (recommended)
make dev-local

# Public access via tunnel (for sharing/testing)
make dev-tunnel
```

That's it! Services start automatically with the right configuration.

## Common Commands

| Command | Purpose |
|---------|---------|
| `make dev-local` | Start everything (localhost only) |
| `make dev-tunnel` | Start everything (public HTTPS) |
| `make stop` | Stop all services |
| `make dev-clean` | Clean caches and restart |

## Accessing the App

### Local Mode (`make dev-local`)
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Docs: http://localhost:8000/docs

### Tunnel Mode (`make dev-tunnel`)
- Public URL: https://random-id.trycloudflare.com
- Backend: Proxied through frontend at `/api`
- Logs: `tail -f /tmp/tunnel.log`

## Troubleshooting

### "Network request failed"
```bash
make stop
make dev-tunnel  # Regenerates correct config
```

### Webpack errors
```bash
make dev-clean  # Clears all caches
```

### Database connection errors
```bash
docker compose ps  # Check if PostgreSQL is running
docker compose up -d  # Start if needed
```

## Learn More

- [Full Development Guide](../docs/ai-assistants/CLAUDE.md)
- [Tunnel Documentation](TUNNEL.md)
- [Database Guide](../docs/ai-assistants/CLAUDE.md#database-setup-postgresql-vs-sqlite)
- [API Documentation](http://localhost:8000/docs) (when backend is running)

## Key Project Files

```
frontend/.env.local     # Auto-generated, don't edit!
Makefile                # All available commands
docker-compose.yml      # PostgreSQL + Redis
backend/main.py         # FastAPI app
frontend/src/           # Next.js app
```

## Getting Help

1. Check [CLAUDE.md](../docs/ai-assistants/CLAUDE.md) for detailed guides
2. Check [TUNNEL.md](TUNNEL.md) for tunnel-specific issues
3. Run `make help` to see all available commands
4. Check logs in `/tmp/*.log`
