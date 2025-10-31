SHELL := /bin/bash

.PHONY: help bootstrap install-dev lint test format scrape-sample dev api backend scraper scraper-details frontend db-upgrade db-downgrade db-reset load-data

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
	uvicorn backend.main:app --reload &
	cd frontend && pnpm dev

api: ## Start only the FastAPI backend
	uvicorn backend.main:app --reload

scraper: ## Run full scraper crawl (fighters list)
	.venv/bin/scrapy crawl fighters_list

scraper-details: ## Run scraper for fighter details
	.venv/bin/scrapy crawl fighter_detail -a input_file="data/processed/fighters_list.jsonl"

frontend: ## Start only the Next.js frontend
	cd frontend && pnpm dev

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

load-data: ## Load scraped fighter data into database
	.venv/bin/python -m scripts.load_scraped_data

load-data-sample: ## Load sample fighter data (first 10 fighters)
	.venv/bin/python -m scripts.load_scraped_data --limit 10

