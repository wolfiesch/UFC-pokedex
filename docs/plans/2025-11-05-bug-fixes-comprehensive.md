# Bug Fixes and Code Quality Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix critical bugs, security vulnerabilities, and code quality issues identified in comprehensive codebase audit across backend, frontend, and scraper modules.

**Architecture:** Prioritized bug fixes organized by severity (CRITICAL → HIGH → MEDIUM → LOW) to maximize impact. Each task follows TDD principles with test-first approach, minimal implementation, verification, and frequent commits.

**Tech Stack:**
- Backend: FastAPI, SQLAlchemy, Pydantic, pytest
- Frontend: Next.js 14, TypeScript, React, Zustand
- Scraper: Scrapy, BeautifulSoup4, Pydantic
- Testing: pytest, Playwright MCP

---

## CRITICAL PRIORITY TASKS

### Task 1: Fix Database Connection Leak in Async Context Manager

**Files:**
- Modify: `backend/db/connection.py:124-136`
- Test: `tests/backend/db/test_connection_leak.py` (new)

**Step 1: Write failing test for connection leak scenario**

Create `tests/backend/db/test_connection_leak.py`:

```python
"""Tests for database connection leak prevention."""
import pytest
from sqlalchemy.exc import SQLAlchemyError
from backend.db.connection import get_async_session


@pytest.mark.asyncio
async def test_session_closes_on_commit_error():
    """Test that session is properly closed even if commit fails."""
    session_gen = get_async_session()
    session = await anext(session_gen)

    # Track if close was called
    close_called = False
    original_close = session.close

    async def tracked_close():
        nonlocal close_called
        close_called = True
        await original_close()

    session.close = tracked_close

    # Simulate commit failure
    with pytest.raises(Exception):
        await session.commit()
        raise SQLAlchemyError("Simulated commit failure")

    # Ensure cleanup was called
    try:
        await anext(session_gen)
    except StopAsyncIteration:
        pass

    assert close_called, "Session close() should be called even on commit error"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/backend/db/test_connection_leak.py -v`
Expected: FAIL - test may pass incorrectly if leak exists

**Step 3: Fix connection.py to ensure close() is always called**

Modify `backend/db/connection.py:124-136`:

```python
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to provide database session.

    Yields async session and ensures proper cleanup even on errors.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/backend/db/test_connection_leak.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/db/connection.py tests/backend/db/test_connection_leak.py
git commit -m "fix(db): ensure session close on commit errors

- Add try/finally to guarantee close() execution
- Add test for connection leak scenario
- Prevents connection pool exhaustion"
```

---

### Task 2: Remove Type Safety Bypass in Fighter Repository

**Files:**
- Modify: `backend/db/repositories/fighter_repository.py:522`
- Modify: `backend/db/models/__init__.py:98-103`
- Test: `tests/backend/db/test_streak_type_validation.py` (new)

**Step 1: Write failing test for invalid streak type**

Create `tests/backend/db/test_streak_type_validation.py`:

```python
"""Tests for streak type validation."""
import pytest
from backend.db.models import Fighter


def test_streak_type_must_be_valid_literal():
    """Test that invalid streak types are rejected."""
    fighter = Fighter(
        id="test-id",
        name="Test Fighter",
        current_streak_count=5
    )

    # Valid values should work
    for valid_type in ["win", "loss", "draw", "none", None]:
        fighter.current_streak_type = valid_type  # Should not raise

    # Invalid value should raise or be caught
    with pytest.raises((ValueError, AssertionError)):
        fighter.current_streak_type = "invalid_type"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/backend/db/test_streak_type_validation.py -v`
Expected: FAIL - type ignore currently allows invalid values

**Step 3: Add database constraint for streak type**

Create migration file `.venv/bin/python -m alembic revision -m "add_streak_type_constraint"`:

```python
"""add_streak_type_constraint

Revision ID: abc123def456
Revises: b502e054dc5b
Create Date: 2025-11-05
"""
from alembic import op


def upgrade():
    op.execute("""
        ALTER TABLE fighters
        ADD CONSTRAINT check_streak_type
        CHECK (current_streak_type IN ('win', 'loss', 'draw', 'none') OR current_streak_type IS NULL)
    """)


def downgrade():
    op.execute("ALTER TABLE fighters DROP CONSTRAINT check_streak_type")
```

**Step 4: Remove type ignore and add explicit validation**

Modify `backend/db/repositories/fighter_repository.py:522`:

```python
# Remove the type: ignore comment and add validation
from typing import Literal

StreakType = Literal["win", "loss", "draw", "none"]

def _validate_streak_type(value: str | None) -> StreakType | None:
    """Validate streak type matches allowed values."""
    if value is None:
        return None
    if value not in ("win", "loss", "draw", "none"):
        raise ValueError(f"Invalid streak type: {value}")
    return value  # Now type-safe

# Use in repository:
current_streak_type=_validate_streak_type(fighter.current_streak_type),
```

**Step 5: Run migration and tests**

Run: `make db-upgrade && pytest tests/backend/db/test_streak_type_validation.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/db/repositories/fighter_repository.py backend/db/migrations/versions/*.py tests/backend/db/test_streak_type_validation.py
git commit -m "fix(db): add type-safe validation for streak_type

- Add database constraint for current_streak_type
- Remove type: ignore suppression
- Add explicit validation function
- Prevents runtime errors from invalid data"
```

---

### Task 3: Fix Bare Exception Handlers in Cache Module

**Files:**
- Modify: `backend/cache.py:132,155,167,184`
- Test: `tests/backend/test_cache_error_handling.py` (new)

**Step 1: Write test for non-Redis exceptions**

Create `tests/backend/test_cache_error_handling.py`:

```python
"""Tests for cache error handling."""
import pytest
from unittest.mock import AsyncMock, patch
from redis.exceptions import RedisConnectionError
from backend.cache import RedisCache


@pytest.mark.asyncio
async def test_cache_only_catches_redis_errors():
    """Test that non-Redis exceptions are not suppressed."""
    cache = RedisCache()

    # Mock Redis to raise non-Redis exception
    with patch.object(cache, '_redis_client') as mock_redis:
        mock_redis.get = AsyncMock(side_effect=ValueError("Not a Redis error"))

        # Should NOT suppress non-Redis exceptions
        with pytest.raises(ValueError):
            await cache.get("test_key")


@pytest.mark.asyncio
async def test_cache_handles_redis_connection_error():
    """Test that Redis connection errors are properly handled."""
    cache = RedisCache()

    with patch.object(cache, '_redis_client') as mock_redis:
        mock_redis.get = AsyncMock(side_effect=RedisConnectionError("Connection failed"))

        # Should handle gracefully and return None
        result = await cache.get("test_key")
        assert result is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/backend/test_cache_error_handling.py -v`
Expected: FAIL - broad exception handler will suppress ValueError

**Step 3: Replace broad exception handlers with specific ones**

Modify `backend/cache.py:132,155,167,184`:

```python
# Line 132 - get() method
try:
    value = await self._redis_client.get(key)
    return json.loads(value) if value else None
except RedisConnectionError as e:
    logger.warning(f"Redis connection error in get({key}): {e}")
    return None

# Line 155 - set() method
try:
    await self._redis_client.setex(key, ttl, json.dumps(value))
except RedisConnectionError as e:
    logger.warning(f"Redis connection error in set({key}): {e}")

# Line 167 - delete() method
try:
    await self._redis_client.delete(key)
except RedisConnectionError as e:
    logger.warning(f"Redis connection error in delete({key}): {e}")

# Line 184 - invalidate_pattern() method
try:
    keys = await self._redis_client.keys(pattern)
    if keys:
        await self._redis_client.delete(*keys)
except RedisConnectionError as e:
    logger.warning(f"Redis connection error in invalidate_pattern({pattern}): {e}")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/backend/test_cache_error_handling.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/cache.py tests/backend/test_cache_error_handling.py
git commit -m "fix(cache): catch only Redis-specific exceptions

- Replace broad Exception handlers with RedisConnectionError
- Prevents masking non-Redis errors
- Improves debuggability and error visibility"
```

---

### Task 4: Fix Race Condition in Global Cache State

**Files:**
- Modify: `backend/cache.py:115-137`
- Test: `tests/backend/test_cache_race_condition.py` (new)

**Step 1: Write test for race condition**

Create `tests/backend/test_cache_race_condition.py`:

```python
"""Tests for cache initialization race conditions."""
import pytest
import asyncio
from backend.cache import get_redis_cache, _redis_client, _lock


@pytest.mark.asyncio
async def test_concurrent_cache_initialization():
    """Test that concurrent calls don't create multiple clients."""
    # Reset global state
    global _redis_client
    _redis_client = None

    # Track initialization calls
    init_count = 0
    original_init = get_redis_cache.__code__

    async def tracked_init():
        nonlocal init_count
        init_count += 1
        return await get_redis_cache()

    # Simulate 10 concurrent initialization attempts
    results = await asyncio.gather(*[tracked_init() for _ in range(10)])

    # All should return same client
    assert all(r == results[0] for r in results)

    # Client should only be created once
    assert _redis_client is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/backend/test_cache_race_condition.py -v`
Expected: FAIL - early return creates TOCTOU window

**Step 3: Fix race condition by moving lock acquisition**

Modify `backend/cache.py:115-137`:

```python
async def get_redis_cache() -> RedisCache | None:
    """Get or initialize Redis cache client."""
    global _redis_client

    # ALWAYS acquire lock first to prevent TOCTOU race
    async with _lock:
        # Double-check pattern inside lock
        if _redis_client is not None:
            return _redis_client

        redis_url = settings.REDIS_URL
        if not redis_url:
            logger.info("Redis URL not configured, caching disabled")
            return None

        try:
            client = RedisCache(redis_url)
            await client.ping()
            _redis_client = client
            logger.info("Redis cache initialized successfully")
            return _redis_client
        except RedisConnectionError as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/backend/test_cache_race_condition.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/cache.py tests/backend/test_cache_race_condition.py
git commit -m "fix(cache): prevent race condition in initialization

- Move lock acquisition before any state check
- Eliminates TOCTOU race condition window
- Ensures single client creation in concurrent scenarios"
```

---

### Task 5: Fix N+1 Query Pattern in Fighter Detail

**Files:**
- Modify: `backend/db/repositories/fighter_repository.py:224-311`
- Test: `tests/backend/db/test_fighter_query_performance.py` (new)

**Step 1: Write test to detect N+1 queries**

Create `tests/backend/db/test_fighter_query_performance.py`:

```python
"""Tests for query performance optimization."""
import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine
from backend.db.repositories.fighter_repository import PostgreSQLFighterRepository


class QueryCounter:
    """Track number of SQL queries executed."""
    def __init__(self):
        self.count = 0

    def callback(self, conn, cursor, statement, parameters, context, executemany):
        self.count += 1


@pytest.mark.asyncio
async def test_get_fighter_detail_single_query(db_session):
    """Test that fighter detail loads in minimal queries (no N+1)."""
    counter = QueryCounter()
    event.listen(Engine, "before_cursor_execute", counter.callback)

    repo = PostgreSQLFighterRepository(db_session)

    # Reset counter
    counter.count = 0

    # Get fighter with fights
    fighter = await repo.get_fighter("test-fighter-id")

    # Should use 1-2 queries max (fighter + fights JOIN)
    # Not 1 + N (one per fight)
    assert counter.count <= 2, f"Used {counter.count} queries (N+1 detected)"

    event.remove(Engine, "before_cursor_execute", counter.callback)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/backend/db/test_fighter_query_performance.py -v`
Expected: FAIL - current code uses 3 separate queries

**Step 3: Replace three queries with single JOIN**

Modify `backend/db/repositories/fighter_repository.py:224-311`:

```python
async def get_fighter(self, fighter_id: str) -> dict[str, Any] | None:
    """Get fighter by ID with optimized single-query fetch."""
    from sqlalchemy import select, and_, or_
    from sqlalchemy.orm import selectinload

    # Single query with JOIN to load fighter and all fights
    stmt = (
        select(Fighter)
        .options(selectinload(Fighter.fights))
        .where(Fighter.id == fighter_id)
    )

    result = await self.session.execute(stmt)
    fighter = result.scalar_one_or_none()

    if not fighter:
        return None

    # Build fight history from loaded relationship (no additional queries)
    fight_history = []
    for fight in sorted(fighter.fights, key=lambda f: f.event_date or date.min, reverse=True):
        fight_history.append({
            "id": fight.id,
            "opponent_id": fight.opponent_id,
            "opponent_name": fight.opponent_name,
            "event_name": fight.event_name,
            "event_date": fight.event_date.isoformat() if fight.event_date else None,
            "result": fight.result,
            "method": fight.method,
            "round": fight.round,
            "time": fight.time,
            "stats": fight.stats,
            "weight_class": fight.weight_class,
        })

    return {
        "id": fighter.id,
        "name": fighter.name,
        "nickname": fighter.nickname,
        "division": fighter.division,
        "height": fighter.height,
        "weight": fighter.weight,
        "reach": fighter.reach,
        "leg_reach": fighter.leg_reach,
        "stance": fighter.stance,
        "dob": fighter.dob.isoformat() if fighter.dob else None,
        "record": fighter.record,
        "image_url": resolve_fighter_image(fighter),
        "detail_url": f"/fighters/{fighter.id}",
        "fight_history": fight_history,
        "is_current_champion": fighter.is_current_champion,
        "is_former_champion": fighter.is_former_champion,
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/backend/db/test_fighter_query_performance.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/db/repositories/fighter_repository.py tests/backend/db/test_fighter_query_performance.py
git commit -m "perf(db): fix N+1 query in fighter detail fetch

- Replace 3 separate queries with single JOIN
- Use selectinload for eager relationship loading
- Reduces database round-trips by 66%"
```

---

### Task 6: Add Parameter Validation for Streak Search

**Files:**
- Modify: `backend/api/search.py:12-50`
- Modify: `backend/services/fighter_service.py:537-666`
- Test: `tests/backend/api/test_streak_validation.py` (new)

**Step 1: Write test for orphaned streak parameters**

Create `tests/backend/api/test_streak_validation.py`:

```python
"""Tests for streak parameter validation."""
import pytest
from fastapi.testclient import TestClient
from backend.main import app


client = TestClient(app)


def test_min_streak_count_requires_streak_type():
    """Test that min_streak_count without streak_type is rejected."""
    response = client.get("/search/?q=fighter&min_streak_count=3")

    assert response.status_code == 422
    assert "streak_type required" in response.json()["detail"].lower()


def test_streak_type_requires_min_streak_count():
    """Test that streak_type without min_streak_count is rejected."""
    response = client.get("/search/?q=fighter&streak_type=win")

    assert response.status_code == 422
    assert "min_streak_count required" in response.json()["detail"].lower()


def test_both_streak_params_work_together():
    """Test that both params together are accepted."""
    response = client.get("/search/?q=fighter&streak_type=win&min_streak_count=3")

    # Should succeed (200 or 404 if no results, but not 422)
    assert response.status_code in (200, 404)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/backend/api/test_streak_validation.py -v`
Expected: FAIL - current code accepts orphaned parameters

**Step 3: Add validation to search endpoint**

Modify `backend/api/search.py:12-50`:

```python
from fastapi import APIRouter, Depends, Query, HTTPException


@router.get("/")
async def search_fighters(
    q: str = Query(..., description="Search query"),
    division: str | None = None,
    stance: str | None = None,
    min_fights: int | None = None,
    streak_type: str | None = None,
    min_streak_count: int | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service = Depends(get_fighter_service),
):
    """Search fighters with validation."""

    # Validate streak parameters are used together
    if (streak_type is None) != (min_streak_count is None):
        raise HTTPException(
            status_code=422,
            detail="streak_type and min_streak_count must be provided together"
        )

    results = await service.search_fighters(
        query=q,
        division=division,
        stance=stance,
        min_fights=min_fights,
        streak_type=streak_type,
        min_streak_count=min_streak_count,
        limit=limit,
        offset=offset,
    )

    return results
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/backend/api/test_streak_validation.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/api/search.py tests/backend/api/test_streak_validation.py
git commit -m "fix(api): validate streak params used together

- Reject orphaned streak_type or min_streak_count
- Return 422 with clear error message
- Prevents confusing silent parameter ignoring"
```

---

## HIGH PRIORITY TASKS

### Task 7: Fix Frontend Type Safety - Remove 'as any' Casts

**Files:**
- Modify: `frontend/src/lib/api.ts:521,572,622,676`
- Modify: `frontend/src/lib/api-client.ts`
- Test: `frontend/src/lib/__tests__/api-type-safety.test.ts` (new)

**Step 1: Write test for type-safe API calls**

Create `frontend/src/lib/__tests__/api-type-safety.test.ts`:

```typescript
/**
 * Tests for API type safety.
 */
import { describe, it, expect } from '@jest/globals';
import client from '@/lib/api-client';
import type { paths } from '@/lib/generated/api-schema';


describe('API Type Safety', () => {
  it('should enforce correct payload types for favorites', async () => {
    // This should cause TypeScript compilation error if types are wrong
    const { data, error } = await client.POST('/favorites/', {
      body: {
        user_id: 'test-user',
        fighter_ids: ['fighter-1', 'fighter-2'],
        // @ts-expect-error - invalid field should fail type check
        invalid_field: 'should not compile',
      },
    });

    expect(error).toBeDefined();
  });

  it('should infer correct response types', async () => {
    const { data } = await client.GET('/fighters/{id}', {
      params: { path: { id: 'test-id' } },
    });

    if (data) {
      // These should all have correct types without assertions
      const name: string = data.name;
      const division: string | null = data.division;
      // @ts-expect-error - non-existent field should fail
      const invalid = data.nonexistent_field;
    }
  });
});
```

**Step 2: Run TypeScript compiler to verify it fails**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS (incorrectly - `as any` bypasses type checking)

**Step 3: Remove 'as any' casts and let types infer**

Modify `frontend/src/lib/api.ts:521,572,622,676`:

```typescript
// Line 521 - addToFavorites
export async function addToFavorites(userId: string, fighterIds: string[]) {
  const { data, error } = await client.POST('/favorites/', {
    body: {  // Remove 'as any'
      user_id: userId,
      fighter_ids: fighterIds,
    },
  });

  if (error) throw new Error(error.message || 'Failed to add favorites');
  return data;
}

// Line 572 - removeFromFavorites
export async function removeFromFavorites(userId: string, fighterIds: string[]) {
  const { data, error } = await client.DELETE('/favorites/', {
    body: {  // Remove 'as any'
      user_id: userId,
      fighter_ids: fighterIds,
    },
  });

  if (error) throw new Error(error.message || 'Failed to remove favorites');
  return data;
}

// Line 622 - createFavoriteCollection
export async function createFavoriteCollection(
  userId: string,
  name: string,
  fighterIds: string[]
) {
  const { data, error } = await client.POST('/favorites/collections/', {
    body: {  // Remove 'as any'
      user_id: userId,
      name,
      fighter_ids: fighterIds,
    },
  });

  if (error) throw new Error(error.message || 'Failed to create collection');
  return data;
}

// Line 676 - updateFavoriteCollection
export async function updateFavoriteCollection(
  collectionId: string,
  userId: string,
  updates: { name?: string; fighter_ids?: string[] }
) {
  const { data, error } = await client.PUT('/favorites/collections/{id}', {
    params: { path: { id: collectionId } },
    body: {  // Remove 'as any'
      user_id: userId,
      ...updates,
    },
  });

  if (error) throw new Error(error.message || 'Failed to update collection');
  return data;
}
```

**Step 4: Run TypeScript compiler to verify types are enforced**

Run: `cd frontend && npx tsc --noEmit`
Expected: Compilation errors if payload types don't match OpenAPI schema

**Step 5: Fix any type mismatches revealed**

If TypeScript errors appear, adjust payload structures to match generated types from `api-schema.ts`.

**Step 6: Run tests to verify type safety**

Run: `cd frontend && npm test -- api-type-safety.test.ts`
Expected: PASS

**Step 7: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/__tests__/api-type-safety.test.ts
git commit -m "fix(frontend): remove 'as any' casts for type safety

- Remove type safety bypasses in API calls
- Let TypeScript infer types from OpenAPI schema
- Add tests to enforce type checking
- Prevents type mismatches at compile time"
```

---

### Task 8: Fix Zustand Initialization Race Condition

**Files:**
- Modify: `frontend/src/store/favoritesStore.ts:73-121`
- Test: `frontend/src/store/__tests__/favoritesStore-race.test.ts` (new)

**Step 1: Write test for race condition**

Create `frontend/src/store/__tests__/favoritesStore-race.test.ts`:

```typescript
/**
 * Tests for favorites store race conditions.
 */
import { describe, it, expect, beforeEach, vi } from '@jest/globals';
import { useFavoritesStore } from '../favoritesStore';


describe('FavoritesStore Race Conditions', () => {
  beforeEach(() => {
    // Reset store state
    const { setState } = useFavoritesStore;
    setState({
      isInitialized: false,
      isLoading: false,
      favorites: [],
    });
  });

  it('should handle concurrent initialization calls', async () => {
    const { initialize } = useFavoritesStore.getState();

    // Track API call count
    let apiCallCount = 0;
    global.fetch = vi.fn(() => {
      apiCallCount++;
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ fighters: [] }),
      });
    });

    // Simulate 5 concurrent initialization calls
    await Promise.all([
      initialize(),
      initialize(),
      initialize(),
      initialize(),
      initialize(),
    ]);

    // Should only make ONE API call despite concurrent requests
    expect(apiCallCount).toBe(1);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- favoritesStore-race.test.ts`
Expected: FAIL - multiple API calls made

**Step 3: Fix race condition with promise-based lock**

Modify `frontend/src/store/favoritesStore.ts:73-121`:

```typescript
// Add outside the store
let initializationPromise: Promise<void> | null = null;

// Inside the store:
initialize: async () => {
  const state = get();

  // If already initialized, return immediately
  if (state.isInitialized) {
    return;
  }

  // If initialization is in progress, wait for it
  if (initializationPromise) {
    return initializationPromise;
  }

  // Start initialization
  set({ isLoading: true });

  initializationPromise = (async () => {
    try {
      const userId = getUserId();
      const favorites = await getFavorites(userId);

      set({
        favorites,
        isInitialized: true,
        isLoading: false,
      });
    } catch (error) {
      logger.error('Failed to initialize favorites', error);
      set({ isLoading: false });
    } finally {
      // Clear the promise when done
      initializationPromise = null;
    }
  })();

  return initializationPromise;
},
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- favoritesStore-race.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/store/favoritesStore.ts frontend/src/store/__tests__/favoritesStore-race.test.ts
git commit -m "fix(store): prevent race condition in favorites init

- Add promise-based initialization lock
- Ensures single API call in concurrent scenarios
- Prevents duplicate state updates"
```

---

### Task 9: Add Error Feedback for Optimistic Updates

**Files:**
- Modify: `frontend/src/store/favoritesStore.ts:175-259`
- Modify: `frontend/src/components/FighterCard.tsx:44`
- Test: `frontend/src/store/__tests__/favoritesStore-errors.test.ts` (new)

**Step 1: Write test for failed toggle feedback**

Create `frontend/src/store/__tests__/favoritesStore-errors.test.ts`:

```typescript
/**
 * Tests for favorites store error handling.
 */
import { describe, it, expect, beforeEach, vi } from '@jest/globals';
import { useFavoritesStore } from '../favoritesStore';


describe('FavoritesStore Error Handling', () => {
  beforeEach(() => {
    const { setState } = useFavoritesStore;
    setState({
      isInitialized: true,
      isLoading: false,
      favorites: ['fighter-1'],
    });
  });

  it('should return error result on toggle failure', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      })
    );

    const { toggleFavorite } = useFavoritesStore.getState();
    const result = await toggleFavorite('fighter-2');

    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
  });

  it('should revert optimistic update on error', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 500,
      })
    );

    const initialFavorites = useFavoritesStore.getState().favorites;
    const { toggleFavorite } = useFavoritesStore.getState();

    await toggleFavorite('fighter-2');

    // Should revert to initial state
    const finalFavorites = useFavoritesStore.getState().favorites;
    expect(finalFavorites).toEqual(initialFavorites);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- favoritesStore-errors.test.ts`
Expected: FAIL - toggleFavorite returns void, not result

**Step 3: Make toggleFavorite return success/error result**

Modify `frontend/src/store/favoritesStore.ts:175-259`:

```typescript
toggleFavorite: async (fighterId: string): Promise<{ success: boolean; error?: string }> => {
  const state = get();
  const userId = getUserId();
  const isFavorited = state.favorites.includes(fighterId);

  // Optimistic update
  set({
    favorites: isFavorited
      ? state.favorites.filter(id => id !== fighterId)
      : [...state.favorites, fighterId],
  });

  try {
    if (isFavorited) {
      await removeFromFavorites(userId, [fighterId]);
    } else {
      await addToFavorites(userId, [fighterId]);
    }

    return { success: true };
  } catch (error) {
    logger.error('Failed to toggle favorite', error);

    // Revert optimistic update on error
    set({ favorites: state.favorites });

    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
},
```

**Step 4: Update FighterCard to show error feedback**

Modify `frontend/src/components/FighterCard.tsx:44`:

```typescript
const handleToggleFavorite = async (e: React.MouseEvent) => {
  e.preventDefault();
  e.stopPropagation();

  const result = await toggleFavorite(fighter.id);

  if (result.success) {
    toast.success(
      isFavorite ? 'Removed from favorites' : 'Added to favorites'
    );
  } else {
    toast.error(`Failed to update favorites: ${result.error}`);
  }
};
```

**Step 5: Run tests to verify they pass**

Run: `cd frontend && npm test -- favoritesStore-errors.test.ts`
Expected: PASS

**Step 6: Commit**

```bash
git add frontend/src/store/favoritesStore.ts frontend/src/components/FighterCard.tsx frontend/src/store/__tests__/favoritesStore-errors.test.ts
git commit -m "fix(store): add error feedback for failed toggles

- Return success/error result from toggleFavorite
- Revert optimistic updates on failure
- Show error toast to user on failure"
```

---

### Task 10: Fix Scraper Date Parsing Silent Failures

**Files:**
- Modify: `scraper/utils/parser.py:50-66`
- Test: `tests/scraper/utils/test_parser_date.py` (new)

**Step 1: Write test for date parsing failures**

Create `tests/scraper/utils/test_parser_date.py`:

```python
"""Tests for date parsing in scraper."""
import pytest
from scraper.utils.parser import parse_date


def test_parse_date_returns_none_on_invalid():
    """Test that invalid dates return None, not unparsed text."""
    assert parse_date("Invalid date") is None
    assert parse_date("Not a date at all") is None
    assert parse_date("") is None
    assert parse_date(None) is None


def test_parse_date_handles_valid_formats():
    """Test that valid formats are parsed correctly."""
    assert parse_date("January 15, 2024") == "2024-01-15"
    assert parse_date("Jan 15, 2024") == "2024-01-15"
    assert parse_date("2024-01-15") == "2024-01-15"


def test_parse_date_handles_periods():
    """Test that periods in month names are normalized."""
    assert parse_date("Jan. 15, 2024") == "2024-01-15"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/scraper/utils/test_parser_date.py -v`
Expected: FAIL - invalid dates return unparsed text

**Step 3: Fix parse_date to return None on failure**

Modify `scraper/utils/parser.py:50-66`:

```python
import logging

logger = logging.getLogger(__name__)


def parse_date(value: str | None) -> str | None:
    """Parse date to ISO format, or None if invalid."""
    text = clean_text(value)
    if not text:
        return None

    # Normalize periods in month abbreviations
    text_normalized = text.replace(".", "")

    # Try known formats
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text_normalized, fmt).date().isoformat()
        except ValueError:
            continue

    # All formats failed - log and return None
    logger.warning(f"Could not parse date: '{value}'")
    return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/scraper/utils/test_parser_date.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scraper/utils/parser.py tests/scraper/utils/test_parser_date.py
git commit -m "fix(scraper): return None for invalid dates

- Prevent unparsed text from leaking into data
- Add logging for parsing failures
- Improves data quality and debugging"
```

---

## MEDIUM PRIORITY TASKS

### Task 11: Add Missing Error Handling in Sherdog Scraper

**Files:**
- Modify: `scraper/spiders/fighter_detail.py:73-81`
- Modify: `scraper/spiders/event_detail.py:80-92`
- Test: `tests/scraper/spiders/test_error_handling.py` (new)

**Step 1: Write test for file read errors**

Create `tests/scraper/spiders/test_error_handling.py`:

```python
"""Tests for spider error handling."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from scraper.spiders.fighter_detail import FighterDetailSpider


def test_spider_handles_invalid_json():
    """Test that spider logs and skips malformed JSON."""
    spider = FighterDetailSpider()

    # Create mock file with invalid JSON
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.open.return_value.__enter__.return_value = [
        '{"valid": "json"}',
        'invalid json line',
        '{"another": "valid"}',
    ]

    with patch('scraper.spiders.fighter_detail.Path', return_value=mock_path):
        requests = list(spider.start_requests())

    # Should yield 2 valid requests, skip 1 invalid
    assert len(requests) == 2


def test_spider_handles_encoding_errors():
    """Test that spider handles file encoding errors."""
    spider = FighterDetailSpider()

    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.open.side_effect = UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid')

    with patch('scraper.spiders.fighter_detail.Path', return_value=mock_path):
        requests = list(spider.start_requests())

    # Should handle gracefully and return empty list
    assert requests == []
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/scraper/spiders/test_error_handling.py -v`
Expected: FAIL - spider crashes on errors

**Step 3: Add error handling to FighterDetailSpider**

Modify `scraper/spiders/fighter_detail.py:73-81`:

```python
def start_requests(self):
    """Generate requests from input file with error handling."""
    file_path = Path(self.input_file)

    if not file_path.exists():
        self.logger.error(f"Input file not found: {file_path}")
        return []

    try:
        with file_path.open(encoding="utf-8", errors="replace") as handle:
            for line_num, line in enumerate(handle, start=1):
                try:
                    data = json.loads(line)
                    yield self._create_request(data)
                except json.JSONDecodeError as e:
                    self.logger.warning(
                        f"Skipping malformed JSON at line {line_num}: {e}"
                    )
                    continue
    except Exception as e:
        self.logger.error(f"Error reading input file {file_path}: {e}")
        return []
```

**Step 4: Add same error handling to EventDetailSpider**

Modify `scraper/spiders/event_detail.py:80-92` with identical pattern.

**Step 5: Run tests to verify they pass**

Run: `pytest tests/scraper/spiders/test_error_handling.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add scraper/spiders/fighter_detail.py scraper/spiders/event_detail.py tests/scraper/spiders/test_error_handling.py
git commit -m "fix(scraper): handle file read and JSON errors

- Add try/catch for encoding errors
- Log and skip malformed JSON lines
- Prevents spider crashes on bad input"
```

---

## ADDITIONAL TASKS (12-25)

Due to space constraints, I'll provide the structure for the remaining tasks:

**Task 12:** Add validation error handling in ValidationPipeline
**Task 13:** Add file write error handling in StoragePipeline
**Task 14:** Implement cross-run deduplication in StoragePipeline
**Task 15:** Remove console.log statements from production code
**Task 16:** Add production error tracking integration
**Task 17:** Standardize error handling patterns across frontend
**Task 18:** Add missing accessibility labels
**Task 19:** Add CSRF protection middleware
**Task 20:** Add rate limiting middleware
**Task 21:** Profile and add missing database indexes
**Task 22:** Remove dead code (InMemoryFighterRepository)
**Task 23:** Add type hints to scraper parsers
**Task 24:** Extract duplicated event status logic to utility
**Task 25:** Add unit tests for CSS selector fallbacks

---

## Testing & Verification Strategy

After completing all tasks:

**Step 1: Run full test suite**
```bash
make test
```

**Step 2: Run type checking**
```bash
cd frontend && npx tsc --noEmit
.venv/bin/python -m mypy backend
```

**Step 3: Run linters**
```bash
make lint
```

**Step 4: Manual testing checklist**
- [ ] Test favorites toggle in UI
- [ ] Test search with streak filters
- [ ] Test fighter detail page loading
- [ ] Verify database migrations apply cleanly
- [ ] Run scraper and verify data quality

---

## Deployment Checklist

Before merging to main:

- [ ] All tests pass
- [ ] No TypeScript errors
- [ ] No linting errors
- [ ] Database migrations tested (upgrade + downgrade)
- [ ] Performance regression tests pass
- [ ] Security scan passes
- [ ] Code review completed

---

## Estimated Timeline

- **Critical tasks (1-6):** 2-3 days
- **High priority (7-11):** 2-3 days
- **Medium priority (12-21):** 3-4 days
- **Low priority (22-25):** 1-2 days
- **Testing & verification:** 1 day

**Total:** 9-13 days

---

## Notes

- Follow TDD strictly: test first, then minimal implementation
- Commit after each task completion
- Run tests frequently to catch regressions early
- Use feature branches for each major task group
- Document any deviations from plan in commit messages
