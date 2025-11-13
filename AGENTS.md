# Repository Guidelines

## Project Structure & Module Organization
Backend code lives in `backend/` (FastAPI + SQLAlchemy) with migrations under `alembic/`. Frontend UI and shared hooks/components sit in `frontend/src/`, while `frontend/public/` stores static assets. Scrapy spiders and enrichment utilities live in `scraper/`, with runnable helpers inside `scripts/`. Canonical datasets, fixtures, and backups stay in `data/` and are consumed by both the API and the scraper. Automated suites reside in `tests/`; exploratory smoke flows live in `tests/manual/`. Refer to `docs/` for runbooks, AI guides, and operational checklists before editing shared workflows.

## Build, Test, and Development Commands
- `make bootstrap` – installs Python (via `uv`) and Node dependencies; run after cloning.
- `make dev-local` – brings up FastAPI and Next.js on localhost using your current database.
- `make api:dev` / `make frontend` – start either side independently with PostgreSQL (requires `DATABASE_URL`).
- `make lint`, `make format`, `make test` – run Ruff + Next lint, apply formatters, then execute pytest and Vitest.
- `make scraper`, `make reload-data` – rebuild the fighter corpus; pair these with `make api:seed` for quick sample data.

## Coding Style & Naming Conventions
Python follows Ruff defaults: 4-space indents, 100-character lines, and type-annotated interfaces. Keep modules `snake_case.py`, classes `PascalCase`, and prefer dependency injection for services. Run `ruff format` before committing; `mypy` should stay clean whenever you touch models or schemas. Frontend code uses TypeScript + Prettier (`pnpm format`) with Tailwind class sorting. Co-locate React components under `frontend/src/components/<feature>/` using `PascalCase.tsx`, and keep reusable hooks in `frontend/src/lib/`.

## Testing Guidelines
`pytest` targets `tests/` by default; name files `test_<feature>.py` and keep fixtures in `tests/conftest.py`. Slow or manual flows belong in `tests/manual/` and must be invoked explicitly (e.g., `PYTHONPATH=. uv run python tests/manual/test_comprehensive_webapp.py`). Frontend units live under `frontend/src/**/__tests__/` and run with `pnpm test` (Vitest + Testing Library). When adding endpoints or components, include regression tests plus coverage for error paths; keep branch coverage at or above the current report (~80% reported via `pytest --cov`).

## Commit & Pull Request Guidelines
Commits mirror the existing log: imperative, descriptive subject lines (e.g., “Add Sherdog fight history workflow”) with focused scope. Group unrelated work into separate commits to keep reverts trivial. Each PR should describe the change, list test commands you ran, attach before/after screenshots for UI tweaks, and link the relevant issue or runbook step. Ensure CI-critical targets (`make lint`, `make test`) pass locally before requesting review.

## Security & Configuration Tips
Copy `.env.example` to `.env` and never commit secrets—Docker, Railway, and Cloudflare credentials stay in your local environment managers. Use `make ensure-docker` before scraping or seeding so PostgreSQL/Redis are ready. The project now requires PostgreSQL for all workflows, so ensure `docker compose up -d` is running before touching migrations, Sherdog workflows, or anything under `data/processed/`.
