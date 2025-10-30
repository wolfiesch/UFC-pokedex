# Environment Setup Checklist

This checklist captures the reproducible steps for establishing local tooling required by the UFC Pokedex project.

## Python Backend & Scraper

1. Install Python 3.11 (recommended via `pyenv`).
2. Create a virtual environment:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install -r requirements.txt
   ```
3. Optional (development extras):
   ```bash
   pip install -r requirements-dev.txt
   pre-commit install
   ```

## Node.js Frontend

1. Install Node.js 20 LTS (via `nvm` or `asdf`).
2. From `frontend/`, install dependencies:
   ```bash
   corepack enable
   pnpm install
   # or `npm install` if pnpm is unavailable
   ```
3. Run the development server:
   ```bash
   pnpm dev
   # http://localhost:3000
   ```

## Database & Services

1. Install Docker Desktop (or Docker Engine).
2. Start services with:
   ```bash
   docker compose up -d
   ```
3. Confirm PostgreSQL is reachable on `localhost:5432` with credentials from `.env`.

## Environment Variables

- Copy `.env.example` to `.env` within the project root.
- Required variables:
  ```
  DATABASE_URL=postgresql+psycopg://ufc_pokedex:ufc_pokedex@localhost:5432/ufc_pokedex
  SCRAPER_USER_AGENT=UFC-Pokedex-Scraper/0.1 (+https://github.com/<org>/ufc-pokedex)
  SCRAPER_DELAY_SECONDS=1.5
  ```
- Frontend `.env.local` variables:
  ```
  NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
  ```

## Tooling

- Recommended extensions: VS Code Python, Ruff, ESLint.
- Formatting:
  - Python: Ruff (lint + format), Black optional.
  - Node: Prettier.
- Testing:
  - Python: `pytest`.
  - Frontend: `vitest` (configured via Next.js testing utilities).

## Verification

1. `make check` (runs lint and tests across backend + scraper).
2. `make scrape-sample` (scrapes a small fighter subset and writes to `data/samples`).
3. `make dev` (starts API + frontend concurrently).

