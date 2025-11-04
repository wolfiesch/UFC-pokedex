# Repository Guidelines

## Project Structure & Module Organization
Source lives in `backend/` (FastAPI services), `frontend/` (Next.js 14 UI), and `scraper/` (Scrapy spiders + BeautifulSoup helpers). Shared domain models sit in `ufc_pokedex_project/`. Pytest suites land in `tests/`, while Vitest suites belong inside `frontend/src/**/__tests__`. Operational assets such as docs, ETL scripts, and cached payloads sit in `docs/`, `scripts/`, and `data/` (ignored by git).

## Build, Test, and Development Commands
Run `make bootstrap` once to install Python deps via `uv` plus frontend packages via `pnpm`. Use `make dev` for the full stack in watch mode (FastAPI reload + Next.js dev server). `pnpm build` or `npm run build` compiles the UI bundle. Database migrations use `make db-upgrade` and `make db-downgrade`. Crawlers are exposed through `make scraper` and `make scraper-details`.

## Coding Style & Naming Conventions
Python code follows Ruff formatting (`ruff format`) with 4-space indentation, 100-char lines, and type-annotated public APIs. Keep modules snake_case and prefer singular models (e.g., `fighter_profile.py`). FastAPI routers belong under `backend/api/` with route functions named `list_*` or `get_*`. Frontend code is TypeScript-first; components live in `frontend/src/components` with PascalCase filenames and exported component names. Run `pnpm lint` and `pnpm format` (Prettier + Tailwind plugin) before pushing.

## Testing Guidelines
Execute `make test` to run `pytest` and `pnpm test` together. Standalone Python tests use `pytest -q` from the repo root; place new suites under `tests/` mirroring the source package path. Target coverage is enforced via `pytest-cov` (see `pyproject.toml`)—keep new code covered with unit or async integration tests. Frontend tests rely on Vitest and Testing Library; co-locate specs next to components using `.test.tsx` naming.

## Commit & Pull Request Guidelines
Write commit subjects in imperative mood (`Add fighter detail endpoint`) and keep them under ~72 characters. Group related changes into logical commits; avoid mixing scraper, backend, and frontend edits without a clear reason. Pull requests need: a concise summary, linked issues or plan references, screenshots or terminal output for UI/API changes, and confirmation that formatting, linting, and tests were run locally.

## Environment & Data Notes
Copy `.env.example` for both root and `frontend/` environments; avoid committing secrets. Use `make load-data` to hydrate the database after scraping. Cache artifacts in `data/` only—never store raw scrapes elsewhere.
When running in SQLite mode, use `make api:seed-full` instead of `make api:seed`.
