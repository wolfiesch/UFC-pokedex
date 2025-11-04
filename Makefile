SHELL := /bin/bash

.PHONY: help bootstrap install-dev lint test format scrape-sample dev dev-local dev-clean stop api api-dev api-sqlite api-seed api-seed-full backend scraper scraper-details export-active-fighters export-active-fighters-sample scrape-sherdog-search verify-sherdog-matches verify-sherdog-matches-auto scrape-sherdog-images update-fighter-images sherdog-workflow sherdog-workflow-auto sherdog-workflow-sample frontend db-upgrade db-downgrade db-reset load-data load-data-sample load-data-details load-data-dry-run load-data-details-dry-run reload-data update-records tunnel-frontend tunnel-api tunnel-stop deploy deploy-config deploy-build deploy-test deploy-check ensure-docker docker-up docker-down docker-status

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

ensure-docker: ## Ensure Docker services (PostgreSQL, Redis) are running
	@if ! docker compose ps | grep -q "redis.*Up"; then \
		echo "🐳 Starting Docker services (PostgreSQL + Redis)..."; \
		docker compose up -d; \
		echo "⏳ Waiting for services to be ready..."; \
		sleep 3; \
		echo "✅ Docker services started"; \
	else \
		echo "✅ Docker services already running"; \
	fi

docker-up: ## Start Docker services (PostgreSQL + Redis)
	docker compose up -d
	@echo "✅ Docker services started"

docker-down: ## Stop Docker services
	docker compose down
	@echo "✅ Docker services stopped"

docker-status: ## Show status of Docker services
	docker compose ps

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

dev: ensure-docker ## Start backend, frontend, and Cloudflare tunnels with auto-config
	@echo ""
	@echo "🔄 Stopping existing processes..."
	@pkill cloudflared 2>/dev/null || true
	@lsof -ti :3000 | xargs kill -9 2>/dev/null || true
	@lsof -ti :8000 | xargs kill -9 2>/dev/null || true
	@sleep 1
	@echo ""
	@echo "🚇 Starting Cloudflare tunnels..."
	@TUNNEL_OUTPUT=$$(bash scripts/start_tunnels.sh); \
	FRONTEND_URL=$$(echo "$$TUNNEL_OUTPUT" | grep "FRONTEND_URL=" | cut -d'=' -f2); \
	API_URL=$$(echo "$$TUNNEL_OUTPUT" | grep "API_URL=" | cut -d'=' -f2); \
	echo ""; \
	echo "📝 Updating configuration files..."; \
	sed -i.bak "s|CORS_ALLOW_ORIGINS=.*|CORS_ALLOW_ORIGINS=$$FRONTEND_URL|" .env && rm .env.bak; \
	sed -i.bak "s|NEXT_PUBLIC_API_BASE_URL=.*|NEXT_PUBLIC_API_BASE_URL=$$API_URL|" frontend/.env.local && rm frontend/.env.local.bak; \
	echo ""; \
	echo "🚀 Starting services..."; \
	trap 'pkill cloudflared 2>/dev/null || true; kill 0' INT TERM EXIT; \
	.venv/bin/uvicorn backend.main:app --reload --host $${API_HOST:-0.0.0.0} --port $${API_PORT:-8000} > /tmp/backend.log 2>&1 & \
	sleep 2; \
	cd frontend && pnpm dev > /tmp/frontend.log 2>&1 & \
	sleep 3; \
	echo ""; \
	echo "✅ All services started!"; \
	echo ""; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "📍 LOCAL URLs:"; \
	echo "   Frontend: http://localhost:3000"; \
	echo "   Backend:  http://localhost:8000"; \
	echo ""; \
	echo "🌐 PUBLIC URLs (Cloudflare Tunnels):"; \
	echo "   Frontend: $$FRONTEND_URL"; \
	echo "   Backend:  $$API_URL"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo ""; \
	echo "Press Ctrl+C to stop all services"; \
	tail -f /tmp/backend.log /tmp/frontend.log

api: ensure-docker ## Start only the FastAPI backend (kills existing process on port 8000)
	@echo ""
	@echo "Stopping any existing process on port 8000..."
	@lsof -ti :8000 | xargs kill -9 2>/dev/null || true
	@sleep 1
	@echo "Starting backend..."
	@.venv/bin/uvicorn backend.main:app --reload --host $${API_HOST:-0.0.0.0} --port $${API_PORT:-8000}

api-dev: ## Start backend with auto-reload (without Docker - uses SQLite if DATABASE_URL unset)
	@echo ""
	@echo "🚀 Starting backend in development mode (SQLite if DATABASE_URL not set)..."
	@lsof -ti :8000 | xargs kill -9 2>/dev/null || true
	@sleep 1
	@uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

api-sqlite: ## Start backend with SQLite (forced, no Docker required)
	@echo ""
	@echo "🗄️  Starting backend with SQLite (forced mode)..."
	@lsof -ti :8000 | xargs kill -9 2>/dev/null || true
	@sleep 1
	@USE_SQLITE=1 uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

api-seed: ## Seed database with sample fighters from fixtures
	@echo "🌱 Seeding database with sample fighters..."
	@uv run python -m backend.scripts.seed_fighters ./data/fixtures/fighters.jsonl

api-seed-full: ## Seed database with all fighters from scraped data
	@echo "🌱 Seeding database with all fighters (this may take a while)..."
	@uv run python -m backend.scripts.seed_fighters ./data/processed/fighters_list.jsonl

scraper: ## Run full scraper crawl (fighters list)
	.venv/bin/scrapy crawl fighters_list

scraper-details: ## Run scraper for fighter details (all fighters)
	.venv/bin/scrapy crawl fighter_detail -a input_file="data/processed/fighters_list.jsonl"

scraper-details-missing: ## Run scraper for missing fighter details only
	.venv/bin/python scripts/filter_missing_fighters.py
	@if [ -f data/processed/fighters_missing.jsonl ] && [ -s data/processed/fighters_missing.jsonl ]; then \
		.venv/bin/scrapy crawl fighter_detail -a input_file="data/processed/fighters_missing.jsonl"; \
	fi

export-active-fighters: ## Export active UFC fighters to JSON for Sherdog matching
	.venv/bin/python -m scripts.export_active_fighters

export-active-fighters-sample: ## Export sample fighters for testing (10 fighters)
	.venv/bin/python -m scripts.export_active_fighters --limit 10

scrape-sherdog-search: ## Search Sherdog for UFC fighters and calculate match confidence
	.venv/bin/scrapy crawl sherdog_search

verify-sherdog-matches: ## Interactive CLI to verify ambiguous Sherdog matches
	.venv/bin/python -m scripts.verify_sherdog_matches

verify-sherdog-matches-auto: ## Non-interactive verification (auto-approve ≥70% confidence only)
	.venv/bin/python -m scripts.verify_sherdog_matches --non-interactive

scrape-sherdog-images: ## Download fighter images from Sherdog
	.venv/bin/scrapy crawl sherdog_images

update-fighter-images: ## Update database with Sherdog IDs and image paths
	.venv/bin/python -m scripts.update_fighter_images

sherdog-workflow: ## Run complete Sherdog image scraping workflow (interactive)
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

sherdog-workflow-auto: ## Run complete Sherdog workflow (non-interactive, auto-approve ≥70%)
	@echo "Step 1: Exporting active fighters..."
	@$(MAKE) export-active-fighters
	@echo "\nStep 2: Searching Sherdog for matches..."
	@$(MAKE) scrape-sherdog-search
	@echo "\nStep 3: Verifying matches (auto-approve ≥70% confidence)..."
	@$(MAKE) verify-sherdog-matches-auto
	@echo "\nStep 4: Downloading images..."
	@$(MAKE) scrape-sherdog-images
	@echo "\nStep 5: Updating database..."
	@$(MAKE) update-fighter-images
	@echo "\n✓ Sherdog auto workflow complete!"

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

dev-local: ensure-docker ## Start backend + frontend with localhost URLs (no tunnels, no env changes)
	@echo ""
	@echo "🔄 Stopping existing processes..."
	@lsof -ti :3000 | xargs kill -9 2>/dev/null || true
	@lsof -ti :8000 | xargs kill -9 2>/dev/null || true
	@sleep 1
	@echo ""
	@echo "🚀 Starting services with localhost configuration..."
	@echo ""
	@echo "Starting backend..."
	@.venv/bin/uvicorn backend.main:app --reload --host $${API_HOST:-0.0.0.0} --port $${API_PORT:-8000} > /tmp/backend.log 2>&1 &
	@sleep 2
	@echo "Starting frontend..."
	@cd frontend && pnpm dev > /tmp/frontend.log 2>&1 &
	@sleep 3
	@echo ""
	@echo "✅ All services started!"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📍 URLs:"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Backend:  http://localhost:8000"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "📝 Logs:"
	@echo "   Backend:  tail -f /tmp/backend.log"
	@echo "   Frontend: tail -f /tmp/frontend.log"
	@echo ""
	@echo "Press Ctrl+C to view logs (services will keep running in background)"
	@echo ""
	@trap 'echo ""; echo "Services are still running. To stop them, run: make stop"' INT; \
	tail -f /tmp/backend.log /tmp/frontend.log

stop: ## Stop all running services (backend, frontend, tunnels)
	@echo "🛑 Stopping all services..."
	@lsof -ti :3000 | xargs kill -9 2>/dev/null && echo "  ✓ Frontend stopped" || echo "  - No frontend running"
	@lsof -ti :8000 | xargs kill -9 2>/dev/null && echo "  ✓ Backend stopped" || echo "  - No backend running"
	@pkill cloudflared 2>/dev/null && echo "  ✓ Tunnels stopped" || echo "  - No tunnels running"
	@echo ""
	@echo "✅ All services stopped"
	@echo "💡 Note: Docker services (PostgreSQL, Redis) are still running"
	@echo "   To stop them: make docker-down"

dev-clean: ## Clean frontend caches and restart dev servers (fixes webpack cache issues)
	@echo "🧹 Cleaning frontend build caches and restarting..."
	@echo ""
	@$(MAKE) stop
	@echo ""
	@echo "🗑️  Removing .next, .turbo, and node_modules/.cache..."
	@rm -rf frontend/.next frontend/.turbo frontend/node_modules/.cache
	@echo "  ✓ Caches cleaned"
	@echo ""
	@$(MAKE) dev-local

frontend: ## Start only the Next.js frontend (kills existing process on port 3000)
	@echo "Stopping any existing process on port 3000..."
	@lsof -ti :3000 | xargs kill -9 2>/dev/null || true
	@sleep 1
	@echo "Starting frontend..."
	@cd frontend && pnpm dev

tunnel-frontend: ## Start Cloudflare tunnel for frontend (port 3000)
	cloudflared tunnel --url http://localhost:3000

tunnel-api: ## Start Cloudflare tunnel for API (port 8000)
	cloudflared tunnel --url http://localhost:8000

tunnel-stop: ## Stop all Cloudflare tunnels
	@echo "Stopping all Cloudflare tunnels..."
	@pkill cloudflared 2>/dev/null && echo "✓ Tunnels stopped" || echo "No tunnels running"

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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DEPLOYMENT (cPanel via SSH)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

deploy-config: ## Create deployment configuration from template
	@if [ ! -f .deployment/config.env ]; then \
		cp .deployment/config.env.example .deployment/config.env; \
		echo "✓ Created .deployment/config.env"; \
		echo "⚠️  Please edit .deployment/config.env with your SSH credentials"; \
	else \
		echo "⚠️  .deployment/config.env already exists"; \
	fi

deploy-check: ## Test SSH connection to cPanel server
	@bash scripts/test_ssh.sh

deploy-build: ## Build frontend for production (static export)
	@echo "Building Next.js for production..."
	@cd frontend && BUILD_MODE=static npm run build:static
	@echo "✓ Build complete: frontend/out/"

deploy-test: deploy-build ## Build and test deployment locally
	@echo "Starting local server to preview build..."
	@cd frontend/out && python3 -m http.server 8080

deploy: ## Deploy to cPanel subdomain (builds and uploads via SSH)
	@if [ ! -f .deployment/config.env ]; then \
		echo "❌ Error: .deployment/config.env not found"; \
		echo "Run: make deploy-config"; \
		exit 1; \
	fi
	@bash scripts/deploy.sh

deploy-ftp: ## Deploy to cPanel subdomain via FTP (recommended if SSH fails)
	@if [ ! -f .deployment/config.env ]; then \
		echo "❌ Error: .deployment/config.env not found"; \
		echo "Run: make deploy-config"; \
		exit 1; \
	fi
	@bash scripts/deploy_ftp.sh

deploy-ssh: ## Deploy to cPanel via SSH (faster and more reliable)
	@bash scripts/deploy_ssh.sh

deploy-ssh-test: ## Test SSH connection to cPanel
	@echo "Testing SSH connection..."
	@SSHPASS='EuroBender2024!' sshpass -e ssh -p 21098 -o StrictHostKeyChecking=no wolfdgpl@162.254.39.96 'echo "✓ SSH connection successful!"; pwd; ls -la'
