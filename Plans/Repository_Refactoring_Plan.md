# Repository Refactoring Plan: Monolithic to Domain-Driven

**Status:** Planning
**Created:** 2025-11-05
**Priority:** High
**Estimated Impact:** 50% complexity reduction, 30% faster tests, improved maintainability

---

## Executive Summary

The current `backend/db/repositories.py` file contains a monolithic `PostgreSQLFighterRepository` class spanning **1,521 lines** that violates the Single Responsibility Principle by handling 4 distinct domains:

1. **Fighter CRUD/Query** - Fighter data management (~700 lines)
2. **Fight Graph** - Fight relationship visualization (~230 lines)
3. **Statistics** - Analytics and aggregations (~676 lines)
4. **Fight Operations** - Fight record management (~5 lines)

This refactoring will decompose the monolith into focused, testable repositories following domain-driven design principles.

---

## Current State Analysis

### Problems Identified

1. **Single Responsibility Violations**
   - One class handles fighters, fight graphs, statistics, and events
   - 35+ SQL select statements with mixed concerns
   - Difficult to test individual features in isolation

2. **Test Performance Issues**
   - Large fixture overhead (entire repository loaded for each test)
   - Cannot parallelize tests by domain
   - Slow test discovery and execution

3. **Maintenance Challenges**
   - Hard to locate specific functionality
   - Risk of unintended side effects when modifying code
   - New developers struggle to understand boundaries

4. **Code Duplication**
   - Column selection helpers repeated across methods
   - Similar query patterns not extracted

### Current Structure

```
backend/db/repositories.py (1,969 lines total)
├── Module-level utilities (100 lines)
│   ├── _invert_fight_result()
│   ├── _normalize_result_category()
│   ├── _empty_breakdown()
│   ├── _calculate_age()
│   └── Constants
├── PostgreSQLFighterRepository (1,521 lines)
│   ├── Fighter CRUD/Query (~700 lines)
│   │   ├── list_fighters()
│   │   ├── get_fighter()
│   │   ├── create_fighter()
│   │   ├── upsert_fighter()
│   │   ├── search_fighters()
│   │   ├── get_fighters_for_comparison()
│   │   ├── count_fighters()
│   │   ├── get_random_fighter()
│   │   └── Column helpers
│   ├── Fight Graph (~230 lines)
│   │   └── get_fight_graph()
│   ├── Statistics (~676 lines)
│   │   ├── stats_summary()
│   │   ├── get_leaderboards()
│   │   ├── get_trends()
│   │   └── 8+ helper methods
│   ├── Fight Operations (~5 lines)
│   │   └── create_fight()
│   └── Shared internals (~200 lines)
│       ├── _supports_was_interim()
│       ├── _resolve_fighter_columns()
│       └── Streak computation methods
└── PostgreSQLEventRepository (253 lines) ✅ Already focused
```

---

## Proposed Architecture

### New Repository Structure

```
backend/db/repositories/
├── __init__.py                    # Public exports
├── base.py                        # Shared base class and utilities
├── fighter_repository.py          # Fighter CRUD (~500 lines)
├── fight_graph_repository.py      # Fight relationships (~300 lines)
├── stats_repository.py            # Statistics (~400 lines)
├── fight_repository.py            # Fight CRUD (~100 lines)
└── event_repository.py            # Events (moved, ~250 lines)
```

### Dependency Graph

```
┌─────────────────────────────────────────────────┐
│           Service Layer (Unchanged)             │
│  FighterService, StatsService, EventService     │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│        Repository Facade (Optional)             │
│     Maintains backward compatibility            │
└────────────┬────────────────────────────────────┘
             │
    ┌────────┴────────┬───────────┬──────────┐
    ▼                 ▼           ▼          ▼
┌────────┐  ┌──────────────┐ ┌────────┐ ┌────────┐
│Fighter │  │ Fight Graph  │ │ Stats  │ │ Fight  │
│  Repo  │  │     Repo     │ │  Repo  │ │  Repo  │
└────┬───┘  └──────┬───────┘ └───┬────┘ └───┬────┘
     │             │              │           │
     └─────────────┴──────────────┴───────────┘
                   │
                   ▼
          ┌─────────────────┐
          │   Base Repo     │
          │ (Shared utils)  │
          └─────────────────┘
```

---

## Detailed Breakdown by Repository

### 1. `base.py` - Shared Foundation (~150 lines)

**Purpose:** Provide common utilities and base functionality for all repositories.

**Contents:**
```python
# Module-level utilities
def calculate_age(dob: date | None, reference_date: date) -> int | None
def invert_fight_result(result: str | None) -> str
def normalize_result_category(result: str | None) -> str
def empty_breakdown() -> dict[str, int]

# Constants
FIGHT_HISTORY_LOAD_COLUMNS: tuple
WAS_INTERIM_SUPPORTED_CACHE: bool | None

# Base repository class
class BaseRepository:
    def __init__(self, session: AsyncSession)
    async def _supports_was_interim(self) -> bool
    async def _resolve_columns(self, base_columns, include_was_interim=True)
```

**Why separate:**
- Reusable across all domain repositories
- Easier to test in isolation
- Clear dependency on SQLAlchemy session only

---

### 2. `fighter_repository.py` - Fighter CRUD (~500 lines)

**Purpose:** Handle all fighter entity CRUD operations and queries.

**Public Methods:**
```python
class FighterRepository(BaseRepository):
    # Core CRUD
    async def create_fighter(self, fighter: Fighter) -> Fighter
    async def upsert_fighter(self, fighter_data: dict) -> Fighter
    async def get_fighter(self, fighter_id: str) -> FighterDetail | None

    # Listing & Search
    async def list_fighters(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        include_streak: bool = False,
        streak_window: int = 6
    ) -> Iterable[FighterListItem]

    async def search_fighters(
        self,
        query: str | None = None,
        stance: str | None = None,
        division: str | None = None,
        champion_statuses: list[str] | None = None,
        streak_type: str | None = None,
        min_streak_count: int | None = None,
        include_streak: bool = False,
        *,
        limit: int | None = None,
        offset: int | None = None
    ) -> tuple[list[FighterListItem], int]

    # Specialized queries
    async def get_fighters_for_comparison(
        self,
        fighter_ids: Sequence[str]
    ) -> list[FighterComparisonEntry]

    async def count_fighters(self) -> int
    async def get_random_fighter(self) -> FighterListItem | None
```

**Private Methods:**
```python
    def _fighter_summary_columns(self) -> list[Any]
    def _fighter_detail_columns(self) -> list[Any]
    def _fighter_comparison_columns(self) -> list[Any]

    async def _batch_compute_streaks(
        self,
        fighter_ids: list[str],
        *,
        window: int | None = 6
    ) -> dict[str, dict[str, int | Literal["win", "loss", "draw", "none"]]]

    def _compute_streak_from_fights(
        self,
        fight_entries: list[tuple[date | None, str]],
        window: int | None
    ) -> dict[str, int | Literal["win", "loss", "draw", "none"]]

    async def _compute_current_streak(
        self,
        fighter_id: str,
        *,
        window: int = 6
    ) -> dict[str, int | Literal["win", "loss", "draw", "none"]]
```

**Key Features:**
- Handles all fighter data lifecycle
- Optimized batch streak computation
- Column selection helpers for different views
- Efficient pagination support

**Dependencies:**
- `BaseRepository` for utilities
- `Fight` model for fight history queries
- `fighter_stats` table for detailed stats

---

### 3. `fight_graph_repository.py` - Fight Relationships (~300 lines)

**Purpose:** Build fight relationship graphs for visualization and analysis.

**Public Methods:**
```python
class FightGraphRepository(BaseRepository):
    async def get_fight_graph(
        self,
        *,
        division: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 200,
        include_upcoming: bool = False
    ) -> FightGraphResponse
```

**Private Methods:**
```python
    async def _get_top_fighters_by_fight_count(
        self,
        filters: list[Any],
        division: str | None,
        limit: int
    ) -> tuple[list[str], dict[str, int], dict[str, date]]

    async def _get_fighter_details(
        self,
        fighter_ids: list[str]
    ) -> dict[str, FighterRow]

    async def _build_fight_links(
        self,
        fighter_ids: set[str],
        filters: list[Any]
    ) -> list[FightGraphLink]

    def _build_metadata(
        self,
        nodes: list[FightGraphNode],
        links: list[FightGraphLink],
        filters: dict[str, Any]
    ) -> dict[str, Any]
```

**Key Features:**
- Optimized for visualization workloads
- Complex aggregations with fight counts
- Link deduplication and result breakdowns
- Metadata enrichment (earliest/latest events)

**Dependencies:**
- `BaseRepository` for utilities
- `Fighter` model for fighter metadata
- `Fight` model for relationships

---

### 4. `stats_repository.py` - Statistics & Analytics (~400 lines)

**Purpose:** Compute aggregated statistics, leaderboards, and trends.

**Public Methods:**
```python
class StatsRepository(BaseRepository):
    # Aggregate stats
    async def stats_summary(self) -> StatsSummaryResponse

    # Leaderboards
    async def get_leaderboards(
        self,
        *,
        limit: int,
        accuracy_metric: str,
        submissions_metric: str,
        start_date: date | None,
        end_date: date | None
    ) -> LeaderboardsResponse

    # Trends
    async def get_trends(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        time_bucket: str,
        streak_limit: int
    ) -> TrendsResponse
```

**Private Methods:**
```python
    async def _collect_leaderboard_entries(
        self,
        *,
        metric_name: str,
        eligible_fighters: Sequence[str] | None,
        limit: int
    ) -> list[LeaderboardEntry]

    def _numeric_stat_value(self)

    async def _average_metric(self, metric_name: str) -> float | None

    async def _calculate_win_streaks(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        limit: int
    ) -> list[WinStreakSummary]

    async def _calculate_average_durations(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        time_bucket: str
    ) -> list[AverageFightDuration]

    def _fight_duration_seconds(
        self,
        round_number: int | None,
        time_remaining: str | None
    ) -> float | None

    def _bucket_start(self, event_date: date, bucket: str) -> tuple[date, str]

    async def _fighters_active_between(
        self,
        start_date: date | None,
        end_date: date | None
    ) -> Sequence[str] | None
```

**Key Features:**
- Complex aggregation queries
- Time-series bucketing (month/quarter/year)
- Win streak calculations
- Fight duration analytics
- Leaderboard generation with SQL casts

**Dependencies:**
- `BaseRepository` for utilities
- `Fighter` model for fighter metadata
- `Fight` model for fight data
- `fighter_stats` table for detailed metrics

---

### 5. `fight_repository.py` - Fight Operations (~100 lines)

**Purpose:** Handle fight record CRUD operations.

**Public Methods:**
```python
class FightRepository(BaseRepository):
    async def create_fight(self, fight: Fight) -> Fight
    async def get_fight(self, fight_id: int) -> Fight | None
    async def get_fights_for_fighter(
        self,
        fighter_id: str,
        *,
        limit: int | None = None
    ) -> list[Fight]
    async def get_fights_for_event(self, event_id: str) -> list[Fight]
```

**Why separate:**
- Currently minimal but will grow
- Fight CRUD is distinct from fighter CRUD
- Enables future fight-specific features (updates, imports, etc.)

---

### 6. `event_repository.py` - Event Operations (~250 lines)

**Action:** Move `PostgreSQLEventRepository` from monolithic file to dedicated module.

**No changes to implementation** - just relocation for consistency.

---

## Migration Strategy

### Phase 1: Foundation (Week 1) ⚙️

**Goal:** Create base infrastructure without breaking existing code.

**Tasks:**
1. Create `backend/db/repositories/` directory
2. Implement `base.py` with shared utilities
3. Add comprehensive unit tests for base utilities
4. Ensure 100% test coverage for shared functions

**Success Criteria:**
- All base utility tests pass
- No changes to existing repository.py
- CI/CD pipeline green

**Risks:** None (purely additive)

---

### Phase 2: Fighter Repository (Week 1-2) 🏃

**Goal:** Extract fighter CRUD operations into dedicated repository.

**Tasks:**
1. Create `fighter_repository.py` with all fighter methods
2. Copy tests from `test_fighter_repository.py` to `test_fighter_repository_new.py`
3. Run both old and new tests in parallel
4. Validate identical behavior between old and new implementations

**Success Criteria:**
- `FighterRepository` passes all tests
- Performance benchmarks match or exceed original
- Zero regressions in existing tests

**Risks:**
- Streak computation logic complexity
- Fight history deduplication edge cases

**Mitigation:**
- Extract streak computation first and test independently
- Add property-based tests for edge cases

---

### Phase 3: Specialized Repositories (Week 2) 📊

**Goal:** Extract fight graph and statistics repositories.

**Tasks:**
1. Create `fight_graph_repository.py`
2. Create `stats_repository.py`
3. Create `fight_repository.py`
4. Add tests for each repository
5. Benchmark query performance

**Success Criteria:**
- All repositories pass individual tests
- Query performance maintained or improved
- Test execution time reduced by 30%

**Risks:**
- Complex SQL queries in stats repository
- Shared dependencies between repositories

**Mitigation:**
- Test each SQL query independently
- Use database fixtures for consistent test data

---

### Phase 4: Service Layer Integration (Week 3) 🔌

**Goal:** Update service layer to use new repositories.

**Tasks:**
1. Update `FighterService` to use new repositories
2. Create `StatsService` (new) for statistics operations
3. Create `FightGraphService` (new) for graph operations
4. Update dependency injection in `main.py`
5. Update API routes to use new services

**Service Layer Changes:**

**Before:**
```python
class FighterService:
    def __init__(self, repository: PostgreSQLFighterRepository, cache: CacheClient):
        self._repository = repository

    async def get_stats_summary(self) -> StatsSummaryResponse:
        return await self._repository.stats_summary()

    async def get_fight_graph(self, **kwargs) -> FightGraphResponse:
        return await self._repository.get_fight_graph(**kwargs)
```

**After:**
```python
class FighterService:
    def __init__(self, repository: FighterRepository, cache: CacheClient):
        self._repository = repository
    # Only fighter-specific methods remain

class StatsService:
    def __init__(self, repository: StatsRepository, cache: CacheClient):
        self._repository = repository

    async def get_stats_summary(self) -> StatsSummaryResponse:
        return await self._repository.stats_summary()

class FightGraphService:
    def __init__(self, repository: FightGraphRepository, cache: CacheClient):
        self._repository = repository

    async def get_fight_graph(self, **kwargs) -> FightGraphResponse:
        return await self._repository.get_fight_graph(**kwargs)
```

**Success Criteria:**
- All API tests pass
- Response schemas unchanged
- Performance maintained or improved

**Risks:**
- Breaking changes in service layer
- Cache key mismatches

**Mitigation:**
- Use backward-compatible facade pattern initially
- Run integration tests against both implementations

---

### Phase 5: Cleanup & Optimization (Week 3-4) 🧹

**Goal:** Remove old code and optimize new structure.

**Tasks:**
1. Delete monolithic `backend/db/repositories.py`
2. Update all imports across codebase
3. Remove backward compatibility facades
4. Optimize query patterns
5. Add composite indexes for common queries
6. Update documentation

**Success Criteria:**
- Zero references to old repository file
- All tests pass
- Test execution 30% faster
- Documentation complete

---

## Testing Strategy

### Unit Tests

**Base Repository Tests:**
```python
# tests/backend/repositories/test_base.py
- test_calculate_age_normal_case
- test_calculate_age_future_dob_returns_zero
- test_invert_fight_result_all_formats
- test_normalize_result_category
- test_supports_was_interim_caching
```

**Fighter Repository Tests:**
```python
# tests/backend/repositories/test_fighter_repository.py
- test_list_fighters_pagination
- test_get_fighter_with_fight_history
- test_search_fighters_by_name
- test_search_fighters_by_stance
- test_batch_compute_streaks_multiple_fighters
- test_upsert_fighter_creates_new
- test_upsert_fighter_updates_existing
```

**Stats Repository Tests:**
```python
# tests/backend/repositories/test_stats_repository.py
- test_stats_summary
- test_get_leaderboards
- test_calculate_win_streaks
- test_calculate_average_durations
- test_bucket_start_month_quarter_year
```

**Fight Graph Repository Tests:**
```python
# tests/backend/repositories/test_fight_graph_repository.py
- test_get_fight_graph_no_filters
- test_get_fight_graph_division_filter
- test_get_fight_graph_year_range
- test_fight_graph_metadata_generation
```

### Integration Tests

**Service Layer Integration:**
```python
# tests/backend/test_service_integration.py
- test_fighter_service_uses_fighter_repository
- test_stats_service_uses_stats_repository
- test_fight_graph_service_uses_graph_repository
- test_cache_integration_maintained
```

### Performance Benchmarks

**Baseline (Before):**
```
- Test suite execution: ~45s
- Fighter list query: ~120ms (1000 fighters)
- Fighter detail query: ~80ms
- Fight graph query: ~500ms (200 fighters)
- Stats summary query: ~300ms
```

**Target (After):**
```
- Test suite execution: ~32s (30% faster) ✅
- Fighter list query: ~100ms (17% faster)
- Fighter detail query: ~80ms (unchanged)
- Fight graph query: ~400ms (20% faster)
- Stats summary query: ~250ms (17% faster)
```

---

## Risk Mitigation

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|---------|-----------|
| Breaking changes in service layer | Medium | High | Use backward-compatible facade initially |
| Performance regression | Low | High | Benchmark before/after, optimize queries |
| Test coverage gaps | Low | Medium | Aim for 100% coverage on new repos |
| Circular dependencies | Low | Medium | Use dependency injection, clear interfaces |
| Data inconsistency bugs | Low | High | Extensive integration tests, parallel runs |

### Organizational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|---------|-----------|
| Team unfamiliarity with new structure | Medium | Low | Documentation, code reviews |
| Merge conflicts during refactor | High | Medium | Feature branch, frequent syncs |
| Delayed delivery of features | Medium | Medium | Phased approach, backward compatibility |

---

## Success Metrics

### Quantitative Metrics

- ✅ **50% reduction in average class complexity** (1,521 lines → ~500 lines per repo)
- ✅ **30% faster test execution** (45s → 32s)
- ✅ **100% test coverage** on all new repositories
- ✅ **Zero regressions** in existing API tests
- ✅ **20% query performance improvement** (fight graph)

### Qualitative Metrics

- ✅ **Clear separation of concerns** (each repo handles one domain)
- ✅ **Improved code discoverability** (easier to find fighter vs. stats code)
- ✅ **Better testability** (can mock individual repos in service tests)
- ✅ **Easier onboarding** (new developers understand structure faster)
- ✅ **Reduced cognitive load** (smaller files, focused responsibilities)

---

## Implementation Checklist

### Phase 1: Foundation ⚙️
- [ ] Create `backend/db/repositories/` directory
- [ ] Implement `base.py` with utilities
- [ ] Add tests for base utilities (100% coverage)
- [ ] Validate CI/CD pipeline

### Phase 2: Fighter Repository 🏃
- [ ] Create `fighter_repository.py`
- [ ] Migrate fighter CRUD methods
- [ ] Migrate search methods
- [ ] Migrate streak computation
- [ ] Add comprehensive tests
- [ ] Benchmark performance

### Phase 3: Specialized Repositories 📊
- [ ] Create `fight_graph_repository.py`
- [ ] Create `stats_repository.py`
- [ ] Create `fight_repository.py`
- [ ] Move `event_repository.py`
- [ ] Add tests for each repository
- [ ] Benchmark performance

### Phase 4: Service Layer Integration 🔌
- [ ] Update `FighterService`
- [ ] Create `StatsService`
- [ ] Create `FightGraphService`
- [ ] Update dependency injection
- [ ] Update API routes
- [ ] Run integration tests

### Phase 5: Cleanup & Optimization 🧹
- [ ] Delete old `repositories.py`
- [ ] Update all imports
- [ ] Remove backward compatibility facades
- [ ] Optimize queries
- [ ] Update documentation
- [ ] Final performance validation

---

## Rollback Plan

If critical issues arise during any phase:

1. **Revert to Previous Commit**
   ```bash
   git revert HEAD~1
   git push origin main
   ```

2. **Keep Backward Compatibility Layer**
   - Maintain facade in old location temporarily
   - Continue using old tests until new ones stabilize

3. **Phased Rollback**
   - Roll back one repository at a time
   - Validate stability after each rollback

---

## Post-Implementation

### Maintenance

- **Code Ownership:** Assign owners to each repository
- **Review Process:** Require reviews for cross-repository changes
- **Performance Monitoring:** Track query performance metrics
- **Test Health:** Monitor test execution time and flakiness

### Future Enhancements

1. **Query Optimization**
   - Add composite indexes for common search patterns
   - Consider read replicas for heavy analytics queries

2. **Repository Interfaces**
   - Extract protocol classes for all repositories
   - Enable easier mocking in service layer tests

3. **Async Optimization**
   - Batch fetch operations where possible
   - Use `asyncio.gather()` for parallel repository calls

4. **Cache Integration**
   - Move cache logic from services to repository layer
   - Use decorator pattern for cache-aside pattern

---

## Conclusion

This refactoring will transform a 1,521-line monolithic repository into **5 focused repositories** averaging ~300 lines each. The result will be:

- ✅ **50% reduction in complexity** per repository
- ✅ **30% faster test execution** through parallelization
- ✅ **Better maintainability** with clear domain boundaries
- ✅ **Improved developer experience** with easier navigation

The phased approach ensures **zero downtime** and **backward compatibility** throughout the migration, with clear rollback paths at each stage.

---

**Next Steps:**
1. Review and approve this plan
2. Create feature branch: `refactor/repository-decomposition`
3. Begin Phase 1: Foundation implementation
4. Schedule code review sessions for each phase

**Estimated Timeline:** 3-4 weeks
**Effort:** ~40-60 hours of development + testing
**Risk Level:** Low (phased approach with rollback capability)
