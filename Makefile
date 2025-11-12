SHELL := /bin/bash

.PHONY: help bootstrap install-dev lint test check format scrape-sample dev dev-local dev-clean stop api api-dev api-sqlite api-seed api-seed-full backend scraper scraper-details export-active-fighters export-active-fighters-sample scrape-sherdog-search verify-sherdog-matches verify-sherdog-matches-auto scrape-sherdog-images update-fighter-images sherdog-workflow sherdog-workflow-auto sherdog-workflow-sample scrape-sherdog-fight-history scrape-sherdog-fight-history-incremental load-sherdog-fight-history load-sherdog-fight-history-dry-run sherdog-fight-history-workflow scrape-images-wikimedia scrape-images-wikimedia-test scrape-images-orchestrator scrape-images-orchestrator-test scrape-images-orchestrator-all sync-images-to-db review-recent-images remove-bad-images frontend db-upgrade db-downgrade db-reset load-data load-data-sample load-data-details load-data-dry-run load-data-details-dry-run reload-data update-records champions-scrape champions-refresh scraper-events scraper-events-details scraper-events-details-sample load-events load-events-sample load-events-dry-run load-events-details load-events-details-sample load-events-details-dry-run tunnel-frontend tunnel-api tunnel-stop deploy deploy-config deploy-build deploy-test deploy-check ensure-docker docker-up docker-down docker-status

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

check: ## Run linting and test suites together
	$(MAKE) lint
	$(MAKE) test

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
	echo "📝 Configuring runtime environment overrides..."; \
	CORS_ALLOW_ORIGINS="$$FRONTEND_URL"; \
	NEXT_PUBLIC_API_BASE_URL="$$API_URL"; \
	echo "   CORS_ALLOW_ORIGINS=$$CORS_ALLOW_ORIGINS"; \
	echo "   NEXT_PUBLIC_API_BASE_URL=$$NEXT_PUBLIC_API_BASE_URL"; \
	echo ""; \
	echo "🚀 Starting services..."; \
	trap 'pkill cloudflared 2>/dev/null || true; kill 0' INT TERM EXIT; \
	CORS_ALLOW_ORIGINS="$$FRONTEND_URL" .venv/bin/uvicorn backend.main:app --reload --host $${API_HOST:-0.0.0.0} --port $${API_PORT:-8000} > /tmp/backend.log 2>&1 & \
	sleep 2; \
	echo "🔧 Generating TypeScript types from OpenAPI (background)..."; \
	mkdir -p frontend/src/lib/generated; \
	( \
	  for i in 1 2 3 4 5 6 7 8 9 10; do \
	    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then \
	      echo "✅ Backend ready for type generation"; \
	      cd frontend && pnpm generate:types > /tmp/types.log 2>&1 \
	        && echo "✅ Types generated" \
	        || echo "⚠️  Type generation failed (see /tmp/types.log)"; \
	      exit 0; \
	    fi; \
	    sleep 0.5; \
	  done; \
	  echo "⚠️  Backend not ready after 5s, skipping type generation"; \
	) & \
	DEV_CMD=$${NEXT_DEV_CMD:-dev}; \
	cd frontend && NEXT_PUBLIC_API_BASE_URL="$$API_URL" pnpm run "$$DEV_CMD" > /tmp/frontend.log 2>&1 & \
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

scrape-sherdog-details: ## Scrape detailed fighter stats from Sherdog (DOB, height, reach, etc.)
	.venv/bin/scrapy crawl sherdog_detail

scrape-sherdog-details-sample: ## Scrape Sherdog details for sample fighters (min confidence 70%)
	.venv/bin/scrapy crawl sherdog_detail -a min_confidence=70 -s CLOSESPIDER_ITEMCOUNT=10

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

scrape-sherdog-fight-history: ## Scrape full fight histories from Sherdog for non-UFC fighters
	@echo "🥊 Scraping Sherdog fight histories..."
	@echo "   This will process all fighters in data/processed/non_ufc_fightmatrix_fighters.json"
	PYTHONPATH=. .venv/bin/scrapy crawl sherdog_fight_history

scrape-sherdog-fight-history-incremental: ## Scrape only unscraped fighters (avoids duplicates)
	@echo "🔍 Finding fighters that haven't been scraped yet..."
	@UNSCRAPED_COUNT=$$(PYTHONPATH=. .venv/bin/python scripts/get_unscraped_sherdog_fighters.py 2>&1 | grep "Found" | awk '{print $$2}'); \
	if [ "$$UNSCRAPED_COUNT" = "0" ] || [ -z "$$UNSCRAPED_COUNT" ]; then \
		echo "✅ All fighters already scraped!"; \
		PYTHONPATH=. .venv/bin/python scripts/get_unscraped_sherdog_fighters.py 2>&1 | head -3; \
	else \
		echo "📊 Found $$UNSCRAPED_COUNT unscraped fighters"; \
		echo ""; \
		echo "🥊 Starting incremental scrape..."; \
		PYTHONPATH=. .venv/bin/scrapy crawl sherdog_fight_history; \
	fi

load-sherdog-fight-history: ## Load scraped Sherdog fight histories into database
	@echo "📥 Loading Sherdog fight histories into database..."
	DATABASE_URL="postgresql+psycopg://ufc_pokedex:ufc_pokedex@localhost:5432/ufc_pokedex" \
	PYTHONPATH=. .venv/bin/python scripts/load_sherdog_fight_histories.py

load-sherdog-fight-history-dry-run: ## Preview fight history load without database writes
	@echo "🔍 Dry run - previewing fight history data..."
	DATABASE_URL="postgresql+psycopg://ufc_pokedex:ufc_pokedex@localhost:5432/ufc_pokedex" \
	PYTHONPATH=. .venv/bin/python scripts/load_sherdog_fight_histories.py --dry-run

sherdog-fight-history-workflow: ## Full workflow: scrape unscraped fighters → load to database
	@echo "🚀 Starting Sherdog fight history workflow..."
	@echo ""
	@$(MAKE) scrape-sherdog-fight-history-incremental
	@echo ""
	@echo "📥 Loading scraped data into database..."
	@$(MAKE) load-sherdog-fight-history
	@echo ""
	@echo "✅ Sherdog fight history workflow complete!"

extract-ufc-for-sherdog: ## Extract UFC fighters that need Sherdog enrichment (all ~4,447 fighters)
	@echo "📋 Extracting UFC fighters without Sherdog data..."
	DATABASE_URL="postgresql+psycopg://ufc_pokedex:ufc_pokedex@localhost:5432/ufc_pokedex" \
	PYTHONPATH=. .venv/bin/python scripts/extract_ufc_fighters_for_sherdog.py

extract-ufc-for-sherdog-test: ## Extract 100 UFC fighters for testing
	@echo "📋 Extracting 100 UFC fighters for testing..."
	DATABASE_URL="postgresql+psycopg://ufc_pokedex:ufc_pokedex@localhost:5432/ufc_pokedex" \
	PYTHONPATH=. .venv/bin/python scripts/extract_ufc_fighters_for_sherdog.py --limit 100

scrape-ufc-sherdog-test: ## Test scrape with 100 UFC fighters
	@echo "🧪 Test scraping 100 UFC fighters from Sherdog..."
	@if [ ! -f data/processed/ufc_fighters_for_sherdog.json ]; then \
		echo "📋 Extracting test fighters first..."; \
		$(MAKE) extract-ufc-for-sherdog-test; \
	fi
	PYTHONPATH=. .venv/bin/scrapy crawl sherdog_fight_history \
		-a input_file=data/processed/ufc_fighters_for_sherdog.json

ufc-sherdog-workflow-test: ## Test full workflow with 100 fighters
	@echo "🧪 Testing UFC Sherdog workflow with 100 fighters..."
	@echo ""
	@$(MAKE) extract-ufc-for-sherdog-test
	@echo ""
	@$(MAKE) scrape-ufc-sherdog-test
	@echo ""
	@$(MAKE) load-sherdog-fight-history
	@echo ""
	@echo "✅ Test workflow complete!"

scrape-images-wikimedia: ## Scrape fighter images from Wikimedia Commons (legal, ~20% coverage)
	PYTHONPATH=. .venv/bin/python scripts/wikimedia_image_scraper.py --batch-size 50

scrape-images-wikimedia-test: ## Test Wikimedia scraper with 5 fighters
	PYTHONPATH=. .venv/bin/python scripts/wikimedia_image_scraper.py --test

scrape-images-orchestrator: ## Multi-source image scraper (Wikimedia → Sherdog mapping)
	PYTHONPATH=. .venv/bin/python scripts/image_scraper_orchestrator.py --batch-size 50

scrape-images-orchestrator-test: ## Test orchestrator with 10 fighters
	PYTHONPATH=. .venv/bin/python scripts/image_scraper_orchestrator.py --test

scrape-images-orchestrator-all: ## Run orchestrator on ALL missing fighters (no batch limit)
	@echo "⚠️  This will process ALL fighters missing images (~292)"
	@echo "   Rate limited to 3 seconds per fighter (~15 minutes total)"
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		PYTHONPATH=. .venv/bin/python scripts/image_scraper_orchestrator.py --batch-size 1000; \
	fi

sync-images-to-db: ## Sync images on disk to database (additions + deletions)
	PYTHONPATH=. .venv/bin/python scripts/sync_images_to_db.py

review-recent-images: ## Review recently downloaded images (last 24 hours)
	PYTHONPATH=. .venv/bin/python scripts/review_recent_images.py

remove-bad-images: ## Remove bad images and reset database (edit script first!)
	PYTHONPATH=. .venv/bin/python scripts/remove_bad_images.py

normalize-images: ## Normalize all fighter images to consistent size (300x300 JPEG)
	PYTHONPATH=. .venv/bin/python scripts/normalize_fighter_images.py

normalize-images-dry-run: ## Preview normalization without modifying images
	PYTHONPATH=. .venv/bin/python scripts/normalize_fighter_images.py --dry-run

detect-placeholders: ## Detect Sherdog placeholder images using perceptual hashing
	PYTHONPATH=. .venv/bin/python scripts/detect_placeholder_images.py

detect-placeholders-with-names: ## Detect placeholders and show fighter names
	PYTHONPATH=. .venv/bin/python scripts/detect_placeholder_images.py --with-names

detect-duplicate-photos: ## Find duplicate/similar photos across different fighters
	PYTHONPATH=. .venv/bin/python scripts/detect_duplicate_photos.py

detect-duplicate-photos-exact: ## Find only exact duplicate photos (faster)
	PYTHONPATH=. .venv/bin/python scripts/detect_duplicate_photos.py --exact-only

detect-duplicate-photos-strict: ## Find very similar photos (stricter matching)
	PYTHONPATH=. .venv/bin/python scripts/detect_duplicate_photos.py --similarity 3

review-duplicates: ## Interactive review of duplicate photos with image previews
	PYTHONPATH=. .venv/bin/python scripts/review_duplicates.py

review-duplicates-ascii: ## Review duplicates with ASCII art previews (universal)
	PYTHONPATH=. .venv/bin/python scripts/review_duplicates.py --method ascii

validate-images: ## Validate all fighter images using basic checks
	PYTHONPATH=. .venv/bin/python scripts/validate_fighter_images.py

validate-images-from-file: ## Validate specific fighter IDs from file
	PYTHONPATH=. .venv/bin/python scripts/validate_fighter_images.py --ids-file data/placeholder_fighter_ids.txt

validate-images-facial: ## Validate images with facial detection and quality analysis
	PYTHONPATH=. .venv/bin/python -m backend.scripts.validate_images

validate-images-facial-test: ## Test facial validation on 10 images
	PYTHONPATH=. .venv/bin/python -m backend.scripts.validate_images --limit 10

validate-images-facial-stats: ## Show facial validation statistics
	PYTHONPATH=. .venv/bin/python -m backend.scripts.validate_images --stats

validate-images-facial-force: ## Re-validate all images (including already validated)
	PYTHONPATH=. .venv/bin/python -m backend.scripts.validate_images --force

verify-replacement: ## Verify recently replaced placeholder images (last 2 hours)
	@echo "🔍 Verifying recently replaced images..."
	@PYTHONPATH=. .venv/bin/python scripts/verify_replacement.py

replace-placeholders: ## Replace Sherdog placeholder images with Bing images (batch of 50)
	PYTHONPATH=. .venv/bin/python scripts/replace_placeholder_images.py --batch-size 50 --yes

replace-placeholders-all: ## Replace ALL placeholder images (may take 1+ hours)
	@echo "⚠️  This will replace all 266 placeholder images"
	@echo "   Estimated time: 1-1.5 hours"
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		PYTHONPATH=. .venv/bin/python scripts/replace_placeholder_images.py --batch-size 300 --yes; \
	fi

dev-local: ensure-docker ## Start backend + frontend with localhost URLs (no tunnels)
	@echo ""
	@echo "🔄 Stopping existing processes..."
	@lsof -ti :3000 | xargs kill -9 2>/dev/null || true
	@lsof -ti :8000 | xargs kill -9 2>/dev/null || true
	@sleep 1
	@echo ""
	@echo "⚙️  Configuring localhost environment overrides..."
	@mkdir -p frontend
	@printf '# Auto-generated by `make dev-local` - DO NOT COMMIT\n# Switch back to Cloudflare tunnel URLs with `make dev`\n\nNEXT_PUBLIC_API_BASE_URL=http://localhost:8000\nNEXT_PUBLIC_ASSETS_BASE_URL=http://localhost:8000\n' > frontend/.env.local
	@echo "✅ Configured frontend/.env.local for localhost access"
	@echo ""
	@echo "🚀 Starting services with localhost configuration..."
	@echo ""
	@echo "Starting backend..."
	@.venv/bin/uvicorn backend.main:app --reload --host $${API_HOST:-0.0.0.0} --port $${API_PORT:-8000} > /tmp/backend.log 2>&1 &
	@sleep 2
	@echo "🔧 Generating TypeScript types from OpenAPI (background)..."
	@mkdir -p frontend/src/lib/generated
	@( \
	  for i in 1 2 3 4 5 6 7 8 9 10; do \
	    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then \
	      echo "✅ Backend ready for type generation"; \
	      cd frontend && pnpm generate:types > /tmp/types.log 2>&1 \
	        && echo "✅ Types generated" \
	        || echo "⚠️  Type generation failed (see /tmp/types.log)"; \
	      exit 0; \
	    fi; \
	    sleep 0.5; \
	  done; \
	  echo "⚠️  Backend not ready after 5s, skipping type generation"; \
	) &
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

types-generate: ## Generate TypeScript types from OpenAPI schema (requires backend running)
	@echo "🔧 Generating TypeScript types from OpenAPI..."
	@if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then \
		echo "❌ Backend is not running on http://localhost:8000"; \
		echo "   Please start the backend first with: make api or make api-dev"; \
		exit 1; \
	fi
	@mkdir -p frontend/src/lib/generated
	@cd frontend && pnpm generate:types || npm run generate:types
	@echo "✅ Types generated at frontend/src/lib/generated/api-schema.ts"

tunnel-frontend: ## Start Cloudflare tunnel for frontend (port 3000)
	cloudflared tunnel --url http://localhost:3000

tunnel-api: ## Start Cloudflare tunnel for API (port 8000)
	cloudflared tunnel --url http://localhost:8000

api-tunnel: tunnel-api ## Alias for tunnel-api

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
# CHAMPION DATA OPERATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

champions-scrape: ## Scrape Wikipedia champions and update database
	.venv/bin/python scripts/champions_wiki.py

champions-refresh: ## Full refresh: scrape champions, update DB, regenerate types
	@echo "🏆 Refreshing champion data..."
	@$(MAKE) champions-scrape
	@echo "🔄 Regenerating TypeScript types..."
	@$(MAKE) types-generate
	@echo "✅ Champion data refreshed!"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EVENT DATA OPERATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

scraper-events: ## Scrape UFC events list (upcoming + completed)
	.venv/bin/scrapy crawl events_list

scraper-events-details: ## Scrape detailed fight cards for all events
	@echo "Starting event detail scraper for all events..."
	@echo "This will take ~5-10 minutes (using cache where available)"
	.venv/bin/scrapy crawl event_detail -a input_file="data/processed/events_list.jsonl"

scraper-events-details-sample: ## Scrape fight cards for first 5 events (testing)
	.venv/bin/scrapy crawl event_detail -a input_file="data/processed/events_list.jsonl" -a limit=5

load-events: ## Load scraped event data into database
	PYTHONPATH=. .venv/bin/python scripts/load_events.py

load-events-sample: ## Load sample event data (first 10 events)
	PYTHONPATH=. .venv/bin/python scripts/load_events.py --limit 10

load-events-dry-run: ## Validate event data without inserting into database
	PYTHONPATH=. .venv/bin/python scripts/load_events.py --dry-run

load-events-details: ## Load event details (fight cards) into database
	PYTHONPATH=. .venv/bin/python scripts/load_event_details.py

load-events-details-sample: ## Load sample event details (first 10 events)
	PYTHONPATH=. .venv/bin/python scripts/load_event_details.py --limit 10

load-events-details-dry-run: ## Validate event details without inserting
	PYTHONPATH=. .venv/bin/python scripts/load_event_details.py --dry-run

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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOCATION DATA REFRESH & MONITORING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

refresh-locations-high-priority: ## Refresh high-priority fighters (active with winning streak, limit 100)
	@echo "🔄 Refreshing high-priority fighters..."
	PYTHONPATH=. .venv/bin/python scripts/refresh_fighter_locations.py --priority high --limit 100

refresh-locations-medium-priority: ## Refresh medium-priority fighters (recent but not active, limit 200)
	@echo "🔄 Refreshing medium-priority fighters..."
	PYTHONPATH=. .venv/bin/python scripts/refresh_fighter_locations.py --priority medium --limit 200

refresh-locations-all: ## Refresh all stale location data (>90 days old)
	@echo "🔄 Refreshing all stale location data..."
	PYTHONPATH=. .venv/bin/python scripts/refresh_fighter_locations.py --priority all

refresh-locations-dry-run: ## Preview what would be refreshed (high priority)
	@echo "🔍 Dry run - previewing refresh candidates..."
	PYTHONPATH=. .venv/bin/python scripts/refresh_fighter_locations.py --priority high --dry-run --limit 20

apply-location-overrides: ## Apply manual location overrides from JSON file
	@echo "📝 Applying manual location overrides..."
	PYTHONPATH=. .venv/bin/python scripts/apply_manual_overrides.py --file data/manual/location_overrides.json

apply-location-overrides-dry-run: ## Preview manual overrides without applying
	@echo "🔍 Dry run - previewing manual overrides..."
	PYTHONPATH=. .venv/bin/python scripts/apply_manual_overrides.py --file data/manual/location_overrides.json --dry-run

monitor-location-health: ## Check location data health and coverage
	@PYTHONPATH=. .venv/bin/python scripts/monitor_location_data_health.py

monitor-location-health-json: ## Check location data health (JSON output)
	@PYTHONPATH=. .venv/bin/python scripts/monitor_location_data_health.py --json

.PHONY: scrape-ufc-com-locations scrape-ufc-com-batched match-ufc-com-fighters load-fighter-locations enrich-fighter-locations
scrape-ufc-com-locations: ## Scrape UFC.com list + detail pages for location data
	@echo "🌐 Scraping UFC.com athletes list..."
	PYTHONPATH=. .venv/bin/scrapy crawl ufc_com_athletes
	@echo "🏃 Scraping individual UFC.com athlete profiles..."
	PYTHONPATH=. .venv/bin/scrapy crawl ufc_com_athlete_detail -a input=data/processed/ufc_com_athletes_list.jsonl

scrape-ufc-com-batched: ## Scrape UFC.com athlete profiles in polite batches
	@echo "📦 Running batched UFC.com scrape..."
	PYTHONPATH=. .venv/bin/python scripts/scrape_ufc_com_batched.py

match-ufc-com-fighters: ## Run fuzzy matcher to link UFC.com slugs with UFCStats IDs
	@echo "🤝 Matching UFC.com fighters to UFCStats roster..."
	PYTHONPATH=. .venv/bin/python scripts/match_ufc_com_fighters.py --ufc-com-dir data/processed/ufc_com_fighters --output data/processed/ufc_com_matches.jsonl --manual-review-output data/processed/ufc_com_matches_manual_review.jsonl

load-fighter-locations: ## Load UFC.com + Sherdog location data into the database
	@echo "📥 Loading UFC.com-derived birthplace/training data..."
	PYTHONPATH=. .venv/bin/python scripts/load_ufc_com_locations.py --matches data/processed/ufc_com_matches.jsonl --auto-only
	@echo "🌎 Backfilling Sherdog nationality data..."
	PYTHONPATH=. .venv/bin/python scripts/load_sherdog_nationality.py

enrich-fighter-locations: scrape-ufc-com-locations match-ufc-com-fighters load-fighter-locations ## Full pipeline: scrape → match → load
	@echo "✅ Fighter location enrichment pipeline complete."
