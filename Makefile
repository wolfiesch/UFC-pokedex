SHELL := /bin/bash

.PHONY: help bootstrap install-dev lint test format scrape-sample dev api backend scraper frontend

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

bootstrap: ## Install Python and Node dependencies
	python3 -m pip install --upgrade pip
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	cd frontend && pnpm install || npm install

install-dev: ## Install development-only dependencies
	pip install -r requirements-dev.txt

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

scraper: ## Run scraper crawl
	scrapy crawl fighters_list

frontend: ## Start only the Next.js frontend
	cd frontend && pnpm dev

