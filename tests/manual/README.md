# Manual Test Scripts

These Python scripts reproduce historical end-to-end experiments and smoke tests. They are intentionally **excluded** from the automated `pytest` suite so they can rely on interactive prompts, live services, or brittle timing assumptions.

## What's Here

- `test_comprehensive_webapp.py` – Full-stack navigation through the frontend using Playwright helpers.
- `test_frontend_only.py` / `test_webapp_improved.py` – Focused UI checks for specific flows.
- `test_ufc_app.py`, `test_ufc_pokedex.py`, `test_ufc_app.py` – Legacy Selenium-style harnesses.
- `assets/test_demo.html` – Fixture used by `test_demo.py` for HTML parsing exercises.

## How to Run

1. Activate the virtual environment (`source .venv/bin/activate`) or prefix commands with `uv run`.
2. Export `PYTHONPATH=.` so the scripts can import project modules.
3. Execute a script directly, e.g.:
   ```bash
   PYTHONPATH=. uv run python tests/manual/test_comprehensive_webapp.py
   ```

## Keeping Them Isolated

The repository's `pyproject.toml` marks `tests/manual/` as a `pytest` `norecursedirs`, so standard `make test` runs stay clean. If you add a new exploratory script, document it here and keep any large fixtures inside `tests/manual/assets/`.
