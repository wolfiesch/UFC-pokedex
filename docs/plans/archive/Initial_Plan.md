# UFC Fighter Pokedex - Initial Plan

## Project Overview
A Pokedex-style web application that scrapes fighter data from ufcstats.com and presents it in an interactive, visually appealing interface inspired by the Pokemon Pokedex. The app will automatically update when new data is available on ufcstats.com.

## User Requirements
- **Data Scope**: All available fighter data from ufcstats.com
- **UI Features**:
  - Card-based fighter display
  - Search and filter functionality
  - Detailed fighter pages
  - Collection/favorites tracking
- **Updates**: Automatic data synchronization with ufcstats.com

## Recommended Tech Stack

### Backend
- **Framework**: Python FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Why**: Fast, async support, excellent for REST APIs, type hints

### Scraping
- **Library**: Scrapy (production) + BeautifulSoup4 (exploration)
- **HTTP Client**: httpx for async requests
- **Why**: Scrapy handles rate limiting, retries, concurrent requests automatically

### Frontend
- **Framework**: Next.js 14+ (React with App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React Context + Zustand (for favorites/collections)
- **Why**: SSG/ISR for performance, great DX, SEO-friendly

### DevOps
- **Scheduling**: GitHub Actions or cron jobs
- **Deployment**: Vercel (frontend) + Railway/Render (backend)
- **Caching**: Redis (optional, for API caching)

## Project Structure

```
ufc-pokedex/
├── scraper/                    # Python scraping module
│   ├── __init__.py
│   ├── config.py              # Scraper settings, delays, user agents
│   ├── spiders/
│   │   ├── __init__.py
│   │   ├── fighters_list.py   # Spider for /statistics/fighters
│   │   ├── fighter_detail.py  # Spider for individual fighter pages
│   │   └── events.py          # Spider for events/fights (optional)
│   ├── models/
│   │   ├── __init__.py
│   │   └── fighter.py         # Pydantic models for scraped data
│   ├── pipelines/
│   │   ├── __init__.py
│   │   ├── validation.py      # Data validation pipeline
│   │   └── storage.py         # Database storage pipeline
│   └── utils/
│       ├── __init__.py
│       └── parser.py          # HTML parsing utilities
│
├── backend/                    # FastAPI server
│   ├── __init__.py
│   ├── main.py                # FastAPI app entry point
│   ├── api/
│   │   ├── __init__.py
│   │   ├── fighters.py        # Fighter endpoints
│   │   ├── search.py          # Search/filter endpoints
│   │   └── stats.py           # Statistics endpoints
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── connection.py      # Database connection
│   │   └── migrations/        # Alembic migrations
│   ├── services/
│   │   ├── __init__.py
│   │   ├── fighter_service.py # Business logic
│   │   └── search_service.py  # Search logic
│   └── schemas/
│       ├── __init__.py
│       └── fighter.py         # API response models
│
├── frontend/                   # Next.js application
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx       # Home/fighter list
│   │   │   ├── fighters/
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx  # Fighter detail page
│   │   │   └── favorites/
│   │   │       └── page.tsx   # Favorites collection
│   │   ├── components/
│   │   │   ├── FighterCard.tsx
│   │   │   ├── FighterGrid.tsx
│   │   │   ├── SearchBar.tsx
│   │   │   ├── FilterPanel.tsx
│   │   │   ├── StatsDisplay.tsx
│   │   │   └── Pokedex/
│   │   │       ├── PokedexCard.tsx
│   │   │       └── PokedexModal.tsx
│   │   ├── hooks/
│   │   │   ├── useFighters.ts
│   │   │   ├── useFavorites.ts
│   │   │   └── useSearch.ts
│   │   ├── lib/
│   │   │   ├── api.ts         # API client
│   │   │   └── types.ts       # TypeScript types
│   │   └── store/
│   │       └── favoritesStore.ts  # Zustand store
│   ├── public/
│   │   └── images/            # Placeholder fighter images
│   ├── package.json
│   └── tailwind.config.ts
│
├── scripts/                    # Utility scripts
│   ├── scrape_full.py         # Full scrape script
│   ├── scrape_updates.py      # Incremental update script
│   └── seed_db.py             # Database seeding
│
├── docs/
│   └── plans/
│       └── archive/
│           └── Initial_Plan.md  # This file
│
├── .github/
│   └── workflows/
│       └── scrape_schedule.yml  # GitHub Actions for scheduled scraping
│
├── docker-compose.yml         # Local development with PostgreSQL
├── pyproject.toml             # Python dependencies (requirements.txt archived in docs/legacy/)
└── README.md                  # Project README
```

## Implementation Phases

### Phase 1: Exploration & Setup (Week 1)

**1.1 Manual Exploration**
- Visit ufcstats.com and document the structure
- Identify key pages: fighter list, fighter detail, events, fights
- Note data fields available:
  - Basic: Name, nickname, record (W-L-D), height, weight, reach, stance, DOB
  - Stats: Sig. strikes landed/attempted, takedowns, submissions, knockdowns
  - Fight history: Opponent, result, method, round, time, event
- Use browser DevTools to inspect HTML structure
- Check for pagination, AJAX loading, or dynamic content
- Review robots.txt and scraping policies

**1.2 Project Setup**
- Initialize git repository
- Set up Python virtual environment
- Install dependencies: `scrapy beautifulsoup4 fastapi sqlalchemy psycopg2 pydantic`
- Set up Next.js project: `npx create-next-app@latest frontend --typescript --tailwind --app`
- Create docker-compose.yml for local PostgreSQL
- Initialize project structure

**1.3 Initial Scraper Prototype**
- Create simple BeautifulSoup script to scrape one fighter page
- Validate data extraction works correctly
- Test rate limiting and politeness delays
- Document HTML structure and CSS selectors

### Phase 2: Scraper Development (Week 1-2)

**2.1 Fighter List Spider**
- Build Scrapy spider for http://ufcstats.com/statistics/fighters
- Extract all fighter links and basic info
- Handle pagination (if applicable)
- Implement proper rate limiting (1-2 second delays)
- Add user agent rotation
- Save raw data to JSON for testing

**2.2 Fighter Detail Spider**
- Build spider for individual fighter pages
- Extract comprehensive fighter data:
  - Personal info (name, nickname, age, etc.)
  - Physical stats (height, weight, reach, leg reach)
  - Record (wins, losses, draws, NC)
  - Striking stats (accuracy, defense, strikes per minute)
  - Grappling stats (takedown accuracy/defense, submission attempts)
  - Fight history (complete fight log)
- Handle missing data gracefully
- Validate data format and types

**2.3 Data Pipeline**
- Create Pydantic models for data validation
- Build data cleaning/normalization pipeline
- Handle edge cases (retired fighters, incomplete data)
- Implement deduplication logic
- Add error handling and logging

**2.4 Testing & Validation**
- Test on sample of ~50 fighters
- Verify data accuracy against website
- Check for scraping errors or edge cases
- Optimize scraping speed vs politeness

### Phase 3: Database & Backend API (Week 2-3)

**3.1 Database Design**
```sql
-- Core tables
fighters (
  id SERIAL PRIMARY KEY,
  ufc_stats_id VARCHAR UNIQUE,  -- ID from ufcstats.com URL
  name VARCHAR NOT NULL,
  nickname VARCHAR,
  record VARCHAR,  -- "W-L-D" format
  height_cm DECIMAL,
  weight_lbs DECIMAL,
  reach_cm DECIMAL,
  stance VARCHAR,
  dob DATE,
  -- Stats
  sig_strikes_landed INTEGER,
  sig_strikes_attempted INTEGER,
  takedowns_landed INTEGER,
  takedowns_attempted INTEGER,
  -- Metadata
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  last_scraped_at TIMESTAMP
)

fighter_stats (
  id SERIAL PRIMARY KEY,
  fighter_id INTEGER REFERENCES fighters(id),
  stat_type VARCHAR,  -- 'striking', 'grappling', 'defense'
  stat_name VARCHAR,
  stat_value DECIMAL,
  created_at TIMESTAMP
)

fights (
  id SERIAL PRIMARY KEY,
  fighter_id INTEGER REFERENCES fighters(id),
  opponent_name VARCHAR,
  result VARCHAR,  -- 'W', 'L', 'D', 'NC'
  method VARCHAR,  -- 'KO/TKO', 'Submission', 'Decision', etc.
  round INTEGER,
  time VARCHAR,
  event_name VARCHAR,
  event_date DATE,
  created_at TIMESTAMP
)

-- For future user features
user_favorites (
  id SERIAL PRIMARY KEY,
  user_id INTEGER,  -- If adding user accounts
  fighter_id INTEGER REFERENCES fighters(id),
  created_at TIMESTAMP
)
```

**3.2 FastAPI Setup**
- Initialize FastAPI app with CORS
- Set up database connection with SQLAlchemy
- Create Alembic migrations
- Configure environment variables

**3.3 API Endpoints**

```python
# Fighters
GET /api/fighters
  - Query params: page, limit, search, weight_class, stance, sort
  - Returns: Paginated list of fighters with basic info

GET /api/fighters/:id
  - Returns: Complete fighter data with stats and fight history

GET /api/fighters/:id/stats
  - Returns: Detailed statistics for specific fighter

GET /api/fighters/:id/fights
  - Returns: Fight history for specific fighter

# Search & Filter
GET /api/search
  - Query params: q (search term), filters
  - Returns: Filtered fighter results

GET /api/stats/aggregate
  - Returns: Aggregate stats (total fighters, by weight class, etc.)

# Admin endpoints (for scraping triggers)
POST /api/admin/scrape/full
  - Triggers full scrape (protected)

POST /api/admin/scrape/updates
  - Triggers incremental update (protected)
```

**3.4 Backend Services**
- FighterService: CRUD operations for fighters
- SearchService: Full-text search and filtering logic
- StatsService: Calculate aggregate statistics
- Add caching with Redis (optional optimization)

### Phase 4: Frontend Development (Week 3-4)

**4.1 Core UI Components**

**FighterCard.tsx**
- Pokedex-style card design
- Display fighter image (placeholder initially)
- Show name, nickname, record
- Weight class badge (color-coded)
- Favorite/star button
- Click to view details

**FighterGrid.tsx**
- Responsive grid layout (1/2/3/4 columns)
- Infinite scroll or pagination
- Loading states with skeletons
- Empty states

**SearchBar.tsx**
- Real-time search with debouncing
- Search by name or nickname
- Clear button

**FilterPanel.tsx**
- Filter by:
  - Weight class
  - Stance (Orthodox, Southpaw, Switch)
  - Record (wins/losses ranges)
  - Active status
- Multi-select filters
- Reset filters button

**4.2 Pages**

**Home Page (app/page.tsx)**
- Hero section with search bar
- Fighter grid with all fighters
- Filter panel (sidebar or modal)
- Stats overview (total fighters, etc.)

**Fighter Detail Page (app/fighters/[id]/page.tsx)**
- Large fighter card/header
- Tabbed sections:
  - Overview (bio, physical stats)
  - Statistics (striking, grappling, defense)
  - Fight History (table or timeline)
  - Records & Achievements
- Pokedex-style presentation (think Pokemon details page)
- Share button

**Favorites Page (app/favorites/page.tsx)**
- Grid of favorited fighters
- Stored in localStorage
- Option to export/import favorites

**4.3 Styling & Theme**
- Pokedex-inspired color scheme:
  - Primary: Red (#EE1515)
  - Secondary: Blue (#0075BE)
  - Background: Light gray with subtle texture
- Card designs with beveled edges, shadows
- Weight class color coding:
  - Flyweight: Purple
  - Bantamweight: Blue
  - Featherweight: Green
  - Lightweight: Yellow
  - Welterweight: Orange
  - Middleweight: Red
  - Light Heavyweight: Pink
  - Heavyweight: Gray
- Smooth animations and transitions
- Responsive design (mobile-first)

**4.4 State Management**
- Favorites stored in Zustand + localStorage
- API data cached with SWR or TanStack Query
- Search/filter state in URL params (shareable links)

### Phase 5: Auto-Update System (Week 4)

**5.1 Update Strategy**

**Approach: Hybrid Scheduled + Smart Diffing**
- Full scrape: Monthly (or manual trigger)
- Update scrape: Weekly
- Smart diffing: Only update changed fighters

**5.2 Update Detection**
```python
# scrape_updates.py logic
1. Scrape fighter list page
2. Compare with existing fighters in DB
3. Detect new fighters (not in DB)
4. Detect potentially updated fighters:
   - Changed record (W-L-D)
   - Recent fight date
5. Scrape only new/changed fighters
6. Update database with timestamp
7. Log changes for review
```

**5.3 Scheduling Options**

**Option A: GitHub Actions (Recommended for start)**
```yaml
# .github/workflows/scrape_schedule.yml
name: Scheduled Scrape
on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly on Sunday at 2 AM UTC
  workflow_dispatch:  # Manual trigger
jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - Checkout code
      - Set up Python
      - Install dependencies
      - Run scrape_updates.py
      - Commit changes to DB or trigger API
```

**Option B: Server Cron Job**
- If self-hosting backend, use cron jobs
- More flexible, can run more frequently
- Direct database access

**Option C: API Endpoint + Scheduler**
- POST /api/admin/scrape/updates endpoint
- Call from external service (cron-job.org, EasyCron)
- Protected with API key

**5.4 Change Notifications**
- Log all updates to file
- Optional: Send email/webhook on significant changes
- Dashboard to view recent updates

### Phase 6: Polish & Optimization (Week 5)

**6.1 Performance Optimization**
- Implement ISR (Incremental Static Regeneration) for fighter pages
- Add image optimization (if fighter photos available)
- Database query optimization (indexes, joins)
- API response caching
- Frontend code splitting

**6.2 Additional Features**
- Fighter comparison tool (compare 2-3 fighters side-by-side)
- Statistics visualizations (charts for striking accuracy, etc.)
- Fight timeline/history visualization
- "Random fighter" button
- Advanced search (by record range, stats, etc.)
- Export favorites as CSV or JSON

**6.3 Testing**
- Unit tests for scraper logic
- API endpoint tests
- Frontend component tests
- E2E tests for critical flows
- Load testing for scraper (ensure politeness)

**6.4 Documentation**
- README with setup instructions
- API documentation (OpenAPI/Swagger)
- Scraper documentation (how to run, configure)
- Contributing guide
- Deployment guide

**6.5 Deployment**
- Frontend: Deploy to Vercel
- Backend: Deploy to Railway, Render, or similar
- Database: Managed PostgreSQL (Railway, Supabase, etc.)
- Set up environment variables
- Configure domain (optional)
- Set up monitoring (Sentry for errors)

## Data Scraping Strategy

### Politeness & Ethics
- Add 1-2 second delays between requests
- Respect robots.txt
- Use informative user agent
- Don't scrape during peak hours
- Cache scraped HTML for development
- Handle rate limiting gracefully (exponential backoff)

### Error Handling
- Retry failed requests (max 3 attempts)
- Log all errors with context
- Continue scraping on individual failures
- Alert on repeated failures
- Store partial data to recover from interruptions

### Data Quality
- Validate all scraped data with Pydantic
- Handle missing/malformed data gracefully
- Cross-reference data points for consistency
- Manual review of sample data
- Unit tests for parsers

## Alternative Approaches Considered

### 1. API-First Approach
- **Pros**: Faster, more reliable
- **Cons**: ufcstats.com likely doesn't have public API
- **Decision**: Not viable

### 2. Scraping on Page Load
- **Pros**: Always fresh data
- **Cons**: Slow page loads, high load on ufcstats.com, risk of IP ban
- **Decision**: Rejected - use scheduled scraping instead

### 3. Static Site Only (No Backend)
- **Pros**: Simpler deployment, faster
- **Cons**: No dynamic search, large data files, difficult updates
- **Decision**: Rejected - need backend for search/filter

### 4. Real-time Webscraping API (ScrapingBee, etc.)
- **Pros**: No infrastructure management
- **Cons**: Ongoing costs, less control
- **Decision**: Keep as fallback if direct scraping fails

## Current Scraping Tool Meta (2025)

### For Python:
1. **Scrapy** (Production standard)
   - Best for large-scale scraping
   - Built-in rate limiting, retries, pipelines
   - Steeper learning curve

2. **BeautifulSoup + httpx** (Simple & effective)
   - Easy to learn
   - Great for small-medium projects
   - More manual work for advanced features

3. **Playwright/Selenium** (For JavaScript-heavy sites)
   - Handles dynamic content
   - Slower, more resource-intensive
   - Not needed if ufcstats.com is static HTML

**Recommendation**: Start with BeautifulSoup for exploration, then migrate to Scrapy for production scraping.

## Timeline Summary

- **Week 1**: Exploration, setup, initial scraper prototype
- **Week 2**: Complete scraper, database design, API foundation
- **Week 3**: Backend API completion, start frontend
- **Week 4**: Complete frontend, implement auto-updates
- **Week 5**: Polish, testing, deployment

**Total estimated time**: 4-5 weeks for MVP

## Next Steps

1. **Manual exploration** of ufcstats.com (YOU DO THIS)
   - Document HTML structure
   - Note CSS selectors for data extraction
   - Check pagination and data completeness
   - Test a few pages with browser DevTools

2. **Create simple scraper prototype**
   - Scrape one fighter page
   - Validate data extraction
   - This helps confirm the approach works

3. **Set up project structure**
   - Initialize git repo
   - Create folder structure
   - Set up Python venv and install scrapy/beautifulsoup

4. **Build full scraper**
   - Fighter list spider
   - Fighter detail spider
   - Data validation

5. **Then proceed with backend → frontend → updates**

## Questions to Resolve

1. Does ufcstats.com have fighter photos? If not, use placeholders or find alternative source
2. Are you planning user accounts, or just localStorage favorites?
3. Do you want fight predictions/analysis features? (AI-powered)
4. Hosting budget? (Free tier vs paid)
5. Do you need historical data or just current fighters?

## Resources

- **Scrapy Tutorial**: https://docs.scrapy.org/en/latest/intro/tutorial.html
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Next.js App Router**: https://nextjs.org/docs/app
- **Tailwind CSS**: https://tailwindcss.com/docs
- **PostgreSQL**: https://www.postgresql.org/docs/

---

**Last Updated**: 2025-10-30
**Status**: Initial Planning Phase
