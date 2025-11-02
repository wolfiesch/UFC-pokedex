SHELL := /bin/bash

.PHONY: help bootstrap install-dev lint test format scrape-sample dev api backend scraper scraper-details export-active-fighters export-active-fighters-sample scrape-sherdog-search verify-sherdog-matches scrape-sherdog-images update-fighter-images sherdog-workflow sherdog-workflow-sample frontend db-upgrade db-downgrade db-reset load-data load-data-sample load-data-details load-data-dry-run load-data-details-dry-run reload-data update-records tunnel-frontend tunnel-api

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

bootstrap: ## Install Python and Node dependencies
	uv sync --all-extras
	cd frontend && pnpm install || npm install

install-dev: ## Install development-only dependencies
	uv sync --extra dev

lint: ## Run linters for Python and frontend
	ruff check scraper backend
	cd frontend && pnpm lint || npm run lint

format: ## Format Python and frontend code
	ruff format scraper backend
	cd frontend && pnpm format || npm run format

test: ## Run unit tests across the repo
	pytest
	cd frontend && pnpm test || npm test

scrape-sample: ## Run sample scrape to populate data/samples
	python -m scripts.scrape_sample

dev: ## Start backend and frontend in development mode
	@set -euo pipefail; \
	trap 'kill 0' INT TERM EXIT; \
	.venv/bin/uvicorn backend.main:app --reload --host $${API_HOST:-0.0.0.0} --port $${API_PORT:-8000} & \
	if [ -n "$${WEB_PORT:-}" ]; then \
		cd frontend && PORT=$$WEB_PORT pnpm dev; \
	else \
		cd frontend && pnpm dev; \
	fi

api: ## Start only the FastAPI backend
	.venv/bin/uvicorn backend.main:app --reload

scraper: ## Run full scraper crawl (fighters list)
	.venv/bin/scrapy crawl fighters_list

scraper-details: ## Run scraper for fighter details
	.venv/bin/scrapy crawl fighter_detail -a input_file="data/processed/fighters_list.jsonl"

export-active-fighters: ## Export active UFC fighters to JSON for Sherdog matching
	.venv/bin/python -m scripts.export_active_fighters

export-active-fighters-sample: ## Export sample fighters for testing (10 fighters)
	.venv/bin/python -m scripts.export_active_fighters --limit 10

scrape-sherdog-search: ## Search Sherdog for UFC fighters and calculate match confidence
	.venv/bin/scrapy crawl sherdog_search

verify-sherdog-matches: ## Interactive CLI to verify ambiguous Sherdog matches
	.venv/bin/python -m scripts.verify_sherdog_matches

scrape-sherdog-images: ## Download fighter images from Sherdog
	.venv/bin/scrapy crawl sherdog_images

update-fighter-images: ## Update database with Sherdog IDs and image paths
	.venv/bin/python -m scripts.update_fighter_images

sherdog-workflow: ## Run complete Sherdog image scraping workflow
	@echo "Step 1: Exporting active fighters..."
	@$(MAKE) export-active-fighters
	@echo "\nStep 2: Searching Sherdog for matches..."
	@$(MAKE) scrape-sherdog-search
	@echo "\nStep 3: Verifying matches (interactive)..."
	@$(MAKE) verify-sherdog-matches
	@echo "\nStep 4: Downloading images..."
	@$(MAKE) scrape-sherdog-images
	@echo "\nStep 5: Updating database..."
	@$(MAKE) update-fighter-images
	@echo "\n✓ Sherdog workflow complete!"

sherdog-workflow-sample: ## Run Sherdog workflow with sample data (10 fighters)
	@echo "Step 1: Exporting sample fighters..."
	@$(MAKE) export-active-fighters-sample
	@echo "\nStep 2: Searching Sherdog for matches..."
	@$(MAKE) scrape-sherdog-search
	@echo "\nStep 3: Verifying matches (interactive)..."
	@$(MAKE) verify-sherdog-matches
	@echo "\nStep 4: Downloading images..."
	@$(MAKE) scrape-sherdog-images
	@echo "\nStep 5: Updating database..."
	@$(MAKE) update-fighter-images
	@echo "\n✓ Sherdog sample workflow complete!"

frontend: ## Start only the Next.js frontend
	cd frontend && pnpm dev

tunnel-frontend: ## Start Cloudflare tunnel for frontend (port 3000)
	cloudflared tunnel --url http://localhost:3000

tunnel-api: ## Start Cloudflare tunnel for API (port 8000)
	cloudflared tunnel --url http://localhost:8000

db-upgrade: ## Run database migrations (apply schema changes)
	.venv/bin/python -m alembic upgrade head

db-downgrade: ## Rollback last database migration
	.venv/bin/python -m alembic downgrade -1

db-reset: ## Drop and recreate database (WARNING: destroys all data)
	docker-compose down -v
	docker-compose up -d db
	@echo "Waiting for database to be ready..."
	@sleep 5
	make db-upgrade

load-data: ## Load scraped fighter data (basic list) into database
	.venv/bin/python -m scripts.load_scraped_data $(LOAD_DATA_ARGS)

load-data-sample: ## Load sample fighter data (first 10 fighters)
	.venv/bin/python -m scripts.load_scraped_data --limit 10

load-data-details: ## Load all fighters with full details (from individual JSON files)
	.venv/bin/python -m scripts.load_scraped_data --load-details

load-data-dry-run: ## Validate scraped data without inserting into database
	.venv/bin/python -m scripts.load_scraped_data --dry-run

load-data-details-dry-run: ## Validate detailed fighter data without inserting
	.venv/bin/python -m scripts.load_scraped_data --load-details --dry-run

reload-data: ## Reload fighters list and detail data into database
	@$(MAKE) load-data LOAD_DATA_ARGS="--load-details"

update-records: ## Fast update of fighter records only (~1.5 min for all fighters)
	.venv/bin/python -m scripts.update_fighter_records
