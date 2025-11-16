# UFC-Pokedex Codebase Coupling Analysis

## Executive Summary

This analysis identifies multiple areas of high coupling across both backend and frontend codebases. The most significant coupling issues stem from:

1. **Central hub modules** that many components depend on
2. **Tightly coupled data flow** in the repository layer
3. **Cross-cutting concerns** (caching, image handling) scattered across layers
4. **Service-to-repository tight binding** in the backend
5. **Store-dependent hooks** in the frontend

---

## Backend Coupling Analysis

### Critical Hub Modules

#### 1. `backend.db.models` - THE CENTRAL HUB
**Import count: 16+ files**
**Files:**
- `/home/user/UFC-pokedex/backend/db/repositories/base.py` (line 15)
- `/home/user/UFC-pokedex/backend/db/repositories/fighter_repository.py` (line 26)
- `/home/user/UFC-pokedex/backend/db/repositories/fight_repository.py` (line 11)
- `/home/user/UFC-pokedex/backend/db/repositories/fight_graph_repository.py` (line 17)
- `/home/user/UFC-pokedex/backend/db/repositories/event_repository.py` (line 12)
- `/home/user/UFC-pokedex/backend/db/repositories/ranking_repository.py`
- `/home/user/UFC-pokedex/backend/db/repositories/stats_repository.py`
- `/home/user/UFC-pokedex/backend/api/rankings.py` (line 10)
- `/home/user/UFC-pokedex/backend/api/image_validation.py` (line 12)
- `/home/user/UFC-pokedex/backend/scripts/seed_fighters.py`
- `/home/user/UFC-pokedex/backend/scripts/validate_images.py`
- `/home/user/UFC-pokedex/backend/services/favorites_service.py`
- `/home/user/UFC-pokedex/backend/main.py` (line 169)
- `/home/user/UFC-pokedex/backend/db/migrations/env.py`
- `/home/user/UFC-pokedex/backend/warmup.py` (line 93)

**Coupling Issue:** Every data access layer, service, and API route depends directly on the data models. This creates a bottleneck where any schema change requires updates across the entire codebase.

**Specific Example:**
```python
# /home/user/UFC-pokedex/backend/db/repositories/fighter_repository.py:26
from backend.db.models import Event, Fight, Fighter, FighterRanking, fighter_stats
```
The FighterRepository imports 5 different model classes, each with multiple mapped columns.

#### 2. `backend.cache` - CACHE HUB
**Import count: 8 files**
**Files:**
- `/home/user/UFC-pokedex/backend/main.py`
- `/home/user/UFC-pokedex/backend/services/caching.py` (line 19)
- `/home/user/UFC-pokedex/backend/services/event_service.py`
- `/home/user/UFC-pokedex/backend/services/favorites_service.py`
- `/home/user/UFC-pokedex/backend/services/fight_graph_service.py`
- `/home/user/UFC-pokedex/backend/services/fighter_query_service.py`
- `/home/user/UFC-pokedex/backend/services/stats_service.py`
- `/home/user/UFC-pokedex/backend/warmup.py`

**Coupling Issue:** Multiple services are tightly coupled to the caching infrastructure through `get_cache_client()`. The `@cached` decorator creates implicit dependencies on cache key builders and deserializers.

**Specific Example:**
```python
# /home/user/UFC-pokedex/backend/services/fighter_query_service.py:15-22
from backend.cache import (
    CacheClient,
    comparison_key,
    detail_key,
    get_cache_client,
    list_key,
    search_key,
)
```
The FighterQueryService imports 7 cache-related items directly.

#### 3. `backend.services.image_resolver` - IMAGE HANDLING HUB
**Import count: 3 files (but critical)**
**Files:**
- `/home/user/UFC-pokedex/backend/api/image_validation.py` (line 14)
- `/home/user/UFC-pokedex/backend/db/repositories/fight_graph_repository.py` (line 28)
- `/home/user/UFC-pokedex/backend/db/repositories/fighter_repository.py` (line 45-47)

**Coupling Issue:** Image resolution is embedded into the repository layer, making data retrieval logic dependent on presentation concerns (image path handling).

**Specific Examples:**
```python
# /home/user/UFC-pokedex/backend/db/repositories/fighter_repository.py:631
image_url=resolve_fighter_image(fighter.id, fighter.image_url),
# Called in list_fighters()

# /home/user/UFC-pokedex/backend/db/repositories/fighter_repository.py:888
image_url=resolve_fighter_image(fighter.id, fighter.image_url),
# Called in get_fighter()

# /home/user/UFC-pokedex/backend/db/repositories/fighter_repository.py:1073
image_url=resolve_fighter_image(fighter.id, fighter.image_url),
# Called in search_fighters()

# /home/user/UFC-pokedex/backend/db/repositories/fighter_repository.py:1283
image_url=resolve_fighter_image(fighter.id, fighter.image_url),
# Called in get_random_fighter()

# /home/user/UFC-pokedex/backend/db/repositories/fight_graph_repository.py:102
image_url=resolve_fighter_image_cropped(...)
# Called in fight graph generation

# /home/user/UFC-pokedex/backend/db/repositories/fight_graph_repository.py:146
image_url=resolve_fighter_image_cropped(...)
# Called again in same module
```

This creates 6+ call sites where presentation logic (image URL resolution) is tightly integrated into data retrieval.

---

### Repository Layer Tight Coupling

#### `backend.db.repositories.fighter_repository` - CORE COUPLING POINT
**Lines: 1,778**
**Imports from other repositories:**
- `backend.db.repositories.base` (line 27-32)
- `backend.db.repositories.fight_utils` (line 33-38)

**Coupling Pattern:** FighterRepository contains:
- 1,300+ lines of complex SQL query logic
- 5+ methods that call `resolve_fighter_image()` 
- 5+ methods that call `_fetch_ranking_summaries()`
- Streak computation logic
- Fight history deduplication logic

**Specific High-Coupling Methods:**
```python
# /home/user/UFC-pokedex/backend/db/repositories/fighter_repository.py:517-680
async def list_fighters(...)
# This method:
# - Fetches rankings (line 605)
# - Fetches fight status (line 603)
# - Resolves fighter images (line 631)
# - Computes streaks (line 594)
# TOTAL: 164 lines with 4 different data fetch operations

# /home/user/UFC-pokedex/backend/db/repositories/fighter_repository.py:682-919
async def get_fighter(...)
# This method:
# - Fetches basic fighter info (line 702)
# - Fetches fight stats (line 708)
# - Executes complex CTE UNION query for fights (line 757-762)
# - Fetches opponent names (line 776-779)
# - Deduplicates fights (line 785-853)
# - Sorts fights (line 856)
# - Computes record (line 864)
# - Fetches ranking summaries (line 876)
# - Resolves fighter images (line 888)
# TOTAL: 237 lines with 8 different data fetch operations
```

#### `backend.db.repositories.postgresql_fighter_repository` - REPOSITORY HUB
**Files:**
- `/home/user/UFC-pokedex/backend/db/repositories/fight_graph_repository.py` (line 16)
- `/home/user/UFC-pokedex/backend/db/repositories/fight_repository.py` (line 18)
- `/home/user/UFC-pokedex/backend/db/repositories/fighter_repository.py` (line 19)
- `/home/user/UFC-pokedex/backend/db/repositories/stats_repository.py` (line 19)

**Coupling Issue:** This repository assembles multiple repositories, creating a factory that every service depends on indirectly.

```python
# /home/user/UFC-pokedex/backend/db/repositories/postgresql_fighter_repository.py:16-19
from backend.db.repositories.fight_graph_repository import FightGraphRepository
from backend.db.repositories.fight_repository import FightRepository
from backend.db.repositories.fighter_repository import FighterRepository
from backend.db.repositories.stats_repository import StatsRepository
```

---

### Service-Repository Tight Binding

#### `backend.services.fighter_query_service` - SERVICE HUB
**Imports:**
- `backend.cache` (7 items)
- `backend.db.repositories.fighter_repository` (3 items)
- `backend.services.caching` (2 items)
- `backend.schemas.fighter` (5 items)

**Coupling Issue:** Service is tightly bound to:
1. Specific repository implementation (FighterRepository)
2. Specific cache key builders
3. Specific deserialization functions

**Specific Example - Line 24-30:**
```python
from backend.db.repositories.fighter_repository import (
    FighterRepository,
    FighterSearchFilters,
    filter_roster_entries,
    normalize_search_filters,
    paginate_roster_entries,
)
```
Service imports 5 items from a single repository module.

#### `backend.services.stats_service` - MULTI-REPO COUPLING
**Imports:**
- `backend.db.repositories.fighter_repository` (line 14)
- `backend.db.repositories.stats_repository` (line 15)

**Coupling Issue:** StatsService couples to two different repository implementations without abstraction.

---

### Schemas Creating Bidirectional Dependencies

#### `backend.schemas.fighter` - IMPORTED BY 5 MODULES
**Import locations:**
- `/home/user/UFC-pokedex/backend/api/fighters.py` (lines 3-8)
- `/home/user/UFC-pokedex/backend/db/repositories/fighter_repository.py` (lines 39-44)
- `/home/user/UFC-pokedex/backend/db/repositories/fight_utils.py`
- `/home/user/UFC-pokedex/backend/services/fighter_query_service.py` (lines 31-36)
- `/home/user/UFC-pokedex/backend/api/image_validation.py`

**Coupling Issue:** Repositories import schemas (line 39-44 of fighter_repository.py), creating a dependency from low-level data access to high-level API contracts.

```python
# /home/user/UFC-pokedex/backend/db/repositories/fighter_repository.py:39-44
from backend.schemas.fighter import (
    FighterComparisonEntry,
    FighterDetail,
    FighterListItem,
    FightHistoryEntry,
)
```

---

## Frontend Coupling Analysis

### Critical Hub Modules

#### 1. `@/lib/api` - CENTRAL API CLIENT
**Import count: 15+ files**
**Files importing:**
- `/home/user/UFC-pokedex/frontend/src/store/favoritesStore.ts` (lines 8-12)
- `/home/user/UFC-pokedex/frontend/src/hooks/useFighters.ts` (line 8)
- `/home/user/UFC-pokedex/frontend/src/hooks/useFighterDetails.ts`
- `/home/user/UFC-pokedex/frontend/src/hooks/useStatsHub.ts`
- `/home/user/UFC-pokedex/frontend/src/hooks/useFighter.ts`
- `/home/user/UFC-pokedex/frontend/src/components/FightWeb/FightWebClient.tsx` (line 4)
- Multiple stat/card components

**Coupling Issue:** All API interactions are centralized in one module. Changes to API function signatures require updates across 15+ files.

**Specific Example:**
```typescript
// /home/user/UFC-pokedex/frontend/src/store/favoritesStore.ts:8-13
import {
  getFavoriteCollections,
  getFavoriteCollectionDetail,
  createFavoriteCollection,
  addFavoriteEntry,
  deleteFavoriteEntry,
} from "@/lib/api";
```

#### 2. `@/store/favoritesFiltersStore` - FILTER HUB
**Import count: 6+ files**
**Files importing:**
- `/home/user/UFC-pokedex/frontend/src/hooks/useFavorites.ts` (line 7)
- `/home/user/UFC-pokedex/frontend/src/hooks/useFighters.ts` (line 7)
- Components in favorites section
- Components in explorer section

**Coupling Issue:** Multiple hooks read from this single store, creating tight coupling between components that filter fighters.

```typescript
// /home/user/UFC-pokedex/frontend/src/hooks/useFighters.ts:37-43
const searchTerm = useFavoritesFiltersStore((state) => state.searchTerm);
const stance = useFavoritesFiltersStore((state) => state.stanceFilter);
const division = useFavoritesFiltersStore((state) => state.divisionFilter);
const nationality = useFavoritesFiltersStore((state) => state.nationalityFilter);
const championStatusFilters = useFavoritesFiltersStore((state) => state.championStatusFilters);
const winStreakCount = useFavoritesFiltersStore((state) => state.winStreakCount);
const lossStreakCount = useFavoritesFiltersStore((state) => state.lossStreakCount);
```

#### 3. `@/store/favoritesStore` - FAVORITES HUB
**Import count: 6 files**
**Files importing:**
- `/home/user/UFC-pokedex/frontend/src/hooks/useFavorites.ts` (line 6)
- `/home/user/UFC-pokedex/frontend/src/store/__tests__/favoritesStore-errors.test.ts`
- `/home/user/UFC-pokedex/frontend/src/store/__tests__/favoritesStore-race.test.ts`
- Multiple component files

**Coupling Issue:** All favorites operations go through this single store, which is synchronized with the backend API.

### Component-Level Tight Coupling

#### `@/components/FightWeb/FightWebClient.tsx` - COMPONENT HUB
**Lines: 300+**
**Imports:** 9+ from sibling components
**Import locations:**
```typescript
// /home/user/UFC-pokedex/frontend/src/components/FightWeb/FightWebClient.tsx:4-21
import { getFightGraph } from "@/lib/api";
import type { FightGraphQueryParams, FightGraphResponse } from "@/lib/types";

import { FightGraphCanvas } from "./FightGraphCanvas";
import { FightWebFilters } from "./FightWebFilters";
import { FightWebInsightsPanel } from "./FightWebInsightsPanel";
import { FightWebLegend } from "./FightWebLegend";
import { FightWebSearch } from "./FightWebSearch";
import { FightWebSelectedFighter } from "./FightWebSelectedFighter";
import { FightWebSummary } from "./FightWebSummary";
```

**Coupling Issue:** FightWebClient is the orchestrator for 7 child components. Changes to any child component's props require updates to the parent.

### Store-Hook Tight Binding

#### Hook Dependency Chain
```
useFavorites (hook)
  ├─ useFavoritesStore (store)
  │  └─ @/lib/api (API functions)
  │     └─ api-client (fetch wrapper)
  └─ useFavoritesFiltersStore (store)

useFighters (hook)
  ├─ useFavoritesFiltersStore (store)
  ├─ @/lib/api (API functions)
  └─ TanStack Query (for caching)

useFighter (hook)
  ├─ useFighterDetails (hook)
  └─ @/lib/api (API functions)
```

**Coupling Issue:** Multiple hooks depend on the same stores. A store update affects all consuming hooks across the entire application.

---

## Circular Dependencies

### Identified Circular Patterns

#### Backend - Potential Circular: Repository -> Schema -> Repository
```
fighter_repository.py
  ├─ imports schemas.fighter
  │  └─ no circular
  ├─ imports fight_utils
  │  └─ imports schemas.fighter (line 82 of fight_utils)
  │     └─ no direct loop back
```
No direct circulars, but tight bidirectional dependency between repositories and schemas.

#### Backend - Potential Circular: Service -> Repository -> Models -> Service
```
fighter_query_service
  ├─ imports fighter_repository
  ├─ imports cache
  └─ fighter_repository
      ├─ imports image_resolver (from services)
      └─ imports schemas
```
No direct circular, but cross-layer dependencies create implicit coupling.

#### Frontend - No Direct Circulars
The TypeScript import system prevents most circular dependencies, but there are logical circular references:
```
Store (favoritesStore)
  └─ imports api
     └─ no import back
```

---

## Tight Coupling Patterns Identified

### Pattern 1: "Data Decoration" in Repository Layer
**Issue:** Repositories add presentation-layer concerns (image URLs, formatting) to domain data.
**Examples:**
- `fighter_repository.py:631` - `resolve_fighter_image()` called in `list_fighters()`
- `fighter_repository.py:888` - `resolve_fighter_image()` called in `get_fighter()`
- `fight_graph_repository.py:102` - `resolve_fighter_image_cropped()` called in graph generation

**Impact:** Changes to image handling require updates to 3+ repository methods.

### Pattern 2: "Scattered Caching Concerns"
**Issue:** Caching logic is distributed across services through decorators and manual key building.
**Examples:**
- `fighter_query_service.py` imports 7 cache-related items
- `fight_graph_service.py` uses `@cached` decorator with custom key builders
- `stats_service.py` manually manages cache keys
- `event_service.py` uses CacheableService base class

**Impact:** Cache invalidation or strategy changes require updates across 5+ service files.

### Pattern 3: "Monolithic Repository Methods"
**Issue:** Single repository methods handle multiple concerns.
**Examples:**
- `fighter_repository.list_fighters()` (164 lines) - handles pagination, filtering, ranking lookup, fight status lookup, image resolution, and streak computation
- `fighter_repository.get_fighter()` (237 lines) - handles single fighter fetch, fight history aggregation, opponent lookup, deduplication, and image resolution

**Impact:** Any change to fighter fetching logic requires careful navigation of complex, multi-concern methods.

### Pattern 4: "Hub Module Accumulation"
**Issue:** Modules that do multiple things become central hubs.
**Examples:**
- `backend.cache` - manages Redis/local cache, key builders, TTL logic
- `backend.db.models` - all ORM models in one file
- `@/lib/api` - all API functions and HTTP client setup

**Impact:** Even small changes to these modules ripple through the codebase.

### Pattern 5: "Service-to-Repository Bidirectional Dependency"
**Issue:** Services know about specific repository implementations, and repositories are tightly bound to services for image handling.
**Examples:**
- `fighter_query_service` imports FighterRepository directly
- `stats_service` imports both FighterRepository and StatsRepository directly
- `fight_graph_service` imports FightGraphRepository directly

**Impact:** Cannot swap repository implementations without updating all dependent services.

---

## Quantitative Coupling Metrics

### Backend
- **Hub modules (imported 5+ times):** 3
  - `backend.db.models` (16+ imports)
  - `backend.cache` (8 imports)
  - `backend.schemas.fighter` (5 imports)

- **Hub files (100+ lines with 5+ imports):** 5
  - `fighter_repository.py` (1,778 lines, 5 imports)
  - `fight_graph_repository.py` (500+ lines, 4 imports)
  - `fighter_query_service.py` (400+ lines, 7 imports)
  - `event_service.py` (150+ lines, 4 imports)
  - `stats_service.py` (200+ lines, 5 imports)

- **Coupling hot-spots:** 15+
  - Image resolution: 6 call sites across 3 files
  - Ranking summaries: 5 call sites in 1 file
  - Cache key building: 7 imports in 1 file

### Frontend
- **Hub modules (imported 5+ times):** 2
  - `@/lib/api` (15+ imports)
  - `@/store/favoritesFiltersStore` (6+ imports)

- **Component orchestration points:** 2
  - `FightWebClient.tsx` (9 child imports)
  - `HomePageClient.tsx` (multiple page-level imports)

- **Store-to-Hook coupling:** 6 hooks depend on 2 stores

---

## Recommendations for Decoupling

### Backend - Immediate Actions
1. **Extract image resolution concerns** out of repositories
   - Create a separate mapper/presenter layer
   - Move image handling to API response layer
   
2. **Create repository interfaces**
   - Define abstract repository contracts
   - Allow service-level abstraction of repository choice

3. **Consolidate cache management**
   - Create a cache strategy interface
   - Move cache logic out of individual services

4. **Break up monolithic repository methods**
   - Split `fighter_repository.get_fighter()` into smaller composed methods
   - Create dedicated methods for side-concerns (rankings, fight status)

5. **Separate data model from ORM model**
   - Move models to a separate models submodule
   - Reduce direct ORM model imports across codebase

### Frontend - Immediate Actions
1. **Create API abstraction layer**
   - Introduce facades for API client usage
   - Reduce direct store-to-API imports

2. **Component prop contracts**
   - Reduce orchestrator component imports
   - Use composition over tight component coupling

3. **Store partition**
   - Split large stores into domain-specific smaller stores
   - Reduce store coupling in multiple hooks

---

## Files with Highest Coupling Risk

### Backend (Priority Order)
1. `/home/user/UFC-pokedex/backend/db/repositories/fighter_repository.py` - 1,778 lines, 5+ cross-module imports, 6+ image resolution call sites
2. `/home/user/UFC-pokedex/backend/services/fighter_query_service.py` - 7 cache imports, 3 repository imports
3. `/home/user/UFC-pokedex/backend/db/models/__init__.py` - 400+ lines, 16+ importing files
4. `/home/user/UFC-pokedex/backend/cache.py` - 200+ lines, 8 importing files
5. `/home/user/UFC-pokedex/backend/db/repositories/postgresql_fighter_repository.py` - 4 repository imports

### Frontend (Priority Order)
1. `/home/user/UFC-pokedex/frontend/src/lib/api.ts` - 15+ importing files, all API operations centralized
2. `/home/user/UFC-pokedex/frontend/src/store/favoritesStore.ts` - 6 importing files, backend-synced state
3. `/home/user/UFC-pokedex/frontend/src/store/favoritesFiltersStore.ts` - 6 importing files, widely shared filter state
4. `/home/user/UFC-pokedex/frontend/src/components/FightWeb/FightWebClient.tsx` - 9 component imports, central orchestrator
5. `/home/user/UFC-pokedex/frontend/src/hooks/useFighters.ts` - Imports 2 stores, used by multiple components

