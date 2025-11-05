# UFC Pokedex Bug Scan Report
**Date**: 2025-11-05
**Scan Type**: Comprehensive codebase analysis
**Scope**: Backend API, Services, Repositories, Database Models, Scraper, Frontend, Configuration

---

## 🔴 Critical Issues

### 1. **Incorrect Streak Filtering Logic in `search_fighters` (backend/db/repositories.py:993-1017)**
**Severity**: High
**Location**: `backend/db/repositories.py:993-1017`

**Problem**: The streak filtering is applied AFTER database pagination, which means:
- If you request `limit=20` with a streak filter, the database fetches 20 fighters first
- THEN it filters by streak, potentially returning fewer than 20 results
- The total count is also incorrect after streak filtering

```python
# Lines 973-984: Applies pagination FIRST
if offset is not None and offset > 0:
    stmt = stmt.offset(offset)
if limit is not None and limit > 0:
    stmt = stmt.limit(limit)

result = await self._session.execute(stmt)
fighters = result.scalars().all()

# Lines 1000-1010: THEN filters by streak (too late!)
if streak_type and min_streak_count:
    filtered_fighters = []
    for fighter in fighters:
        # ... streak check
    fighters = filtered_fighters
```

**Impact**:
- Pagination is broken when streak filters are applied
- Users get inconsistent results (e.g., requesting 20 fighters might return 5)
- Total count is misleading

**Fix**: Streak filtering should happen at the database level OR pagination should be applied after streak filtering.

---

### 2. **Potential N+1 Query in Streak Calculation (backend/db/repositories.py:269-327)**
**Severity**: Medium-High
**Location**: `backend/db/repositories.py:269-327`

**Problem**: When `include_streak=True`, the code loads ALL fights for ALL fighters in the current page:
```python
# Line 271-277: Loads fights for all fighters
fights_stmt = select(Fight).where(
    (Fight.fighter_id.in_(fighter_ids))
    | (Fight.opponent_id.in_(fighter_ids))
)
fights_result = await self._session.execute(fights_stmt)
fights = fights_result.scalars().all()
```

**Impact**:
- For a page of 20 fighters, this could load hundreds or thousands of fight records
- No limit on fight history fetched
- Performance degrades as fighter count increases

**Recommendation**: Add a limit to recent fights (e.g., last 10 fights per fighter) or optimize with window functions.

---

### 3. **Missing Database Indexes on Frequently Queried Columns**
**Severity**: Medium
**Location**: `backend/db/models/__init__.py`

**Problem**: Several columns are frequently queried but lack indexes:
- `Fighter.division` (line 65) - Used in search/filter but no index
- `Fighter.stance` (line 70) - Used in search/filter but no index
- `Fight.event_date` (line 123) - Used in date range queries but no index

**Impact**:
- Slow queries as database grows
- Full table scans on every division/stance filter

**Fix**: Add indexes:
```python
division: Mapped[str | None] = mapped_column(String, index=True)
stance: Mapped[str | None] = mapped_column(String, index=True)
event_date: Mapped[date | None] = mapped_column(Date, index=True)
```

---

### 4. **Potential Race Condition in Redis Client Initialization (backend/cache.py:114-136)**
**Severity**: Medium
**Location**: `backend/cache.py:114-136`

**Problem**: Double-checked locking pattern without proper memory barriers:
```python
async def get_redis() -> RedisClient | None:
    global _redis_client
    if _redis_client is None:  # First check (no lock)
        async with _client_lock:
            if _redis_client is None:  # Second check (inside lock)
                # ... initialize
```

**Issue**: In rare cases with asyncio, the first check could see a partially initialized client.

**Impact**: Low probability but could cause connection issues under high concurrency.

**Fix**: Use `asyncio.Lock` more defensively or use `asyncio.create_task` with proper synchronization.

---

## 🟡 Medium Issues

### 5. **Inconsistent Champion Status Filtering (backend/db/repositories.py:952-964)**
**Severity**: Medium
**Location**: `backend/db/repositories.py:952-964`

**Problem**: The `search_fighters` method filters champion status but doesn't include `was_interim`:
```python
for status in champion_statuses:
    if status == "current":
        champion_conditions.append(Fighter.is_current_champion == True)
    elif status == "former":
        champion_conditions.append(Fighter.is_former_champion == True)
    # Missing: elif status == "interim"
```

But the in-memory repository DOES check `was_interim` (line 269 in `fighter_service.py`).

**Impact**: Inconsistent behavior between database and in-memory implementations.

**Fix**: Add support for "interim" status:
```python
elif status == "interim":
    champion_conditions.append(Fighter.was_interim == True)
```

---

### 6. **Hardcoded HTTP Protocol in Fighter URLs (backend/db/repositories.py:336, 565, etc.)**
**Severity**: Low-Medium
**Location**: Multiple locations in `repositories.py`

**Problem**: URLs are hardcoded with `http://` instead of `https://`:
```python
detail_url=f"http://www.ufcstats.com/fighter-details/{fighter.id}",
```

**Impact**:
- External links may fail or redirect
- Security warning in browsers
- ufcstats.com likely uses HTTPS

**Fix**: Change to `https://` or make configurable.

---

### 7. **Potential Type Safety Issue with `typing_cast` (backend/db/repositories.py:355-362)**
**Severity**: Low
**Location**: `backend/db/repositories.py:355-362`

**Problem**: Using `typing_cast` to force a literal type:
```python
current_streak_type=(
    typing_cast(
        Literal["win", "loss", "draw", "none"],
        (streak_by_fighter.get(fighter.id, ("none", 0))[0] if include_streak else "none"),
    )
),
```

**Issue**: If `_normalize_result_category` returns an unexpected value, the cast masks it.

**Impact**: Runtime type errors not caught at compile time.

**Fix**: Validate the value before casting or use an enum.

---

### 8. **Missing Error Handling in Fighter Detail Parsing (scraper/spiders/fighter_detail.py:31-32)**
**Severity**: Medium
**Location**: `scraper/spiders/fighter_detail.py:31-32`

**Problem**: No try-except around parsing:
```python
def parse(self, response: scrapy.http.Response):
    yield parse_fighter_detail_page(response)
```

**Impact**: If parsing fails, the entire spider crashes instead of logging and continuing.

**Fix**: Add error handling:
```python
def parse(self, response: scrapy.http.Response):
    try:
        yield parse_fighter_detail_page(response)
    except Exception as e:
        self.logger.error(f"Failed to parse {response.url}: {e}")
```

---

### 9. **Incorrect URL Building Logic in Scraper (scraper/spiders/fighter_detail.py:61)**
**Severity**: Low
**Location**: `scraper/spiders/fighter_detail.py:61`

**Problem**: Missing protocol in URL:
```python
return [f"http://ufcstats.com/fighter-details/{fighter_id}" for fighter_id in ids]
```

Should be:
```python
return [f"http://www.ufcstats.com/fighter-details/{fighter_id}" for fighter_id in ids]
```

**Impact**: Scraper will fail to fetch fighter details (missing `www.`).

---

### 10. **Duplicate Fight Detection Logic Could Miss Edge Cases (backend/db/repositories.py:436-441)**
**Severity**: Low-Medium
**Location**: `backend/db/repositories.py:436-441`

**Problem**: The `should_replace_fight` function only checks for "N/A" vs actual results:
```python
def should_replace_fight(existing_result: str, new_result: str) -> bool:
    if existing_result == "N/A" and new_result != "N/A":
        return True
    return False
```

**Issue**: Doesn't handle cases where both results exist but differ (e.g., "win" vs "loss").

**Impact**: If the same fight appears twice with conflicting results, the first one is kept (might be wrong).

**Fix**: Add logic to prefer more specific results or log warnings for conflicts.

---

## 🟢 Minor Issues

### 11. **Inconsistent Use of `clean_text` (scraper/utils/parser.py:36-42)**
**Severity**: Low
**Location**: `scraper/utils/parser.py:36-42`

**Problem**: `clean_text` returns `None` for empty strings or "--", but some callers don't handle `None`:
```python
nickname = clean_text(row.css(".b-statistics__nickname::text").get()) or clean_text(...)
```

If both return `None`, `nickname` becomes `None` (correct), but could use `or ""` for consistency.

**Impact**: Very low - mostly cosmetic.

---

### 12. **Magic Numbers in Streak Calculation (backend/db/repositories.py:299, 326)**
**Severity**: Low
**Location**: `backend/db/repositories.py:299, 326`

**Problem**: Hardcoded values without explanation:
```python
recent = entries[: max(2, streak_window)]  # Why 2?
if count >= 2:  # Why 2?
    streak_by_fighter[fid] = (last_type, count)
```

**Fix**: Add comments or constants explaining the minimum streak count.

---

### 13. **Missing Validation in `comparison_key` (backend/cache.py:77-80)**
**Severity**: Low
**Location**: `backend/cache.py:77-80`

**Problem**: No validation that `fighter_ids` is non-empty:
```python
def comparison_key(fighter_ids: Sequence[str]) -> str:
    signature = "|".join(fighter_ids)  # Could be empty string
    digest = sha256(signature.encode("utf-8")).hexdigest()
    return f"{_COMPARISON_PREFIX}:{digest}:{signature}"
```

**Impact**: Empty fighter_ids list creates cache key collision.

**Fix**: Add assertion or raise error if empty.

---

### 14. **Potential Division by Zero (backend/services/fighter_service.py:290, 305)**
**Severity**: Low (already guarded)
**Location**: `backend/services/fighter_service.py:290, 305`

**Status**: SAFE (already has guard), but worth noting:
```python
if node_count <= 1:
    return 0.0
max_edges = (node_count * (node_count - 1)) / 2
if max_edges <= 0:  # Redundant check (good defensive programming)
    return 0.0
```

---

### 15. **Frontend: Missing Error Boundary for Async Operations**
**Severity**: Low
**Location**: `frontend/src/hooks/useFighters.ts`

**Problem**: If `queryFn` throws, the error is caught by TanStack Query, but some edge cases (like network timeout) might not be handled gracefully.

**Impact**: User sees generic error message.

**Fix**: Add more specific error handling in the query function.

---

### 16. **Frontend: Potential Race Condition in Image Cache**
**Severity**: Low
**Location**: Not directly visible in scanned files but implied

**Problem**: Multiple components might request the same image simultaneously, causing duplicate cache entries.

**Impact**: Minor performance issue.

**Fix**: Use request deduplication (e.g., `Promise` memoization).

---

## 📊 Summary Statistics

| Severity | Count |
|----------|-------|
| Critical | 4 |
| Medium   | 6 |
| Low      | 6 |
| **Total**| **16** |

---

## 🔧 Recommended Fixes Priority

1. **Immediate (Fix Now)**:
   - #1: Streak filtering pagination bug
   - #3: Add missing database indexes

2. **High Priority (This Week)**:
   - #2: Optimize streak calculation N+1 query
   - #5: Fix champion status filtering inconsistency
   - #9: Fix scraper URL building

3. **Medium Priority (Next Sprint)**:
   - #4: Redis client race condition
   - #6: Update HTTP to HTTPS
   - #8: Add error handling in scraper

4. **Low Priority (Backlog)**:
   - All remaining low-severity issues

---

## 🧪 Testing Recommendations

1. **Add integration test for streak filtering with pagination**
2. **Load test streak calculation with 1000+ fighters**
3. **Test champion status filter with all combinations**
4. **Test scraper with malformed HTML**
5. **Test Redis connection failures**

---

## ✅ Notes

- Overall code quality is **good** - most issues are edge cases
- The repository pattern is well-implemented
- Type safety is generally excellent (Pydantic + TypeScript)
- Error handling could be more comprehensive in scraper
- Performance optimizations needed for scale (indexes, query optimization)

---

**Scan completed**: All major backend, frontend, and scraper files analyzed.
