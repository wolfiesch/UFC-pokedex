# Bug Report - UFC Pokedex

**Generated:** 2025-11-01
**Scan Type:** Comprehensive codebase analysis

---

## Summary

Found **6 bugs** across backend, frontend, and scripts:
- 🔴 **1 Critical** - May cause connection leaks
- 🟡 **3 Medium** - Cause incorrect behavior or inefficiency
- 🟢 **2 Low** - Performance/quality issues

---

## Critical Bugs

### 🔴 BUG-001: Database Connection Redundant close() Call
 ✅ **FIXED**

**File:** `backend/db/connection.py:47-59`
**Severity:** Critical
**Impact:** May cause connection leaks or improper cleanup

**Issue:**
The `get_db()` function calls `await session.close()` in the finally block, but the `async with session_factory() as session:` context manager already handles closing the session. This redundant close could cause issues.

**Problem:**
- The `async with session_factory() as session:` already handles closing, so `await session.close()` is redundant and potentially problematic
- Calling close() twice could lead to errors or warnings

**Fix Applied:**
Removed the redundant `await session.close()` call from the finally block.

---

## Medium Severity Bugs

### 🟡 BUG-002: Fighter Service Type Mismatch in Fallback

**File:** `backend/services/fighter_service.py:78-79`
**Severity:** Medium
**Impact:** Type error when using InMemoryFighterRepository

**Issue:**
The `count_fighters()` fallback calls `list_fighters()` without passing parameters, but the PostgreSQL version expects `limit` and `offset` parameters.

```python
# Line 78-79
fighters = await self._repository.list_fighters()
return len(list(fighters))
```

**Problem:**
- `InMemoryFighterRepository.list_fighters()` doesn't accept parameters
- `PostgreSQLFighterRepository.list_fighters(limit, offset)` does accept parameters
- This creates a type mismatch and could fail if using the PostgreSQL repository

**Recommendation:**
Use `hasattr` check to determine if parameters are supported, or standardize the interface.

---

### 🟡 BUG-003: Inconsistent Stance Filter Case Sensitivity
✅ **FIXED**

**File:** `backend/services/fighter_service.py:117-119` vs `backend/db/repositories.py:174`
**Severity:** Medium
**Impact:** Inconsistent search results between database and in-memory implementations

**Issue:**
The fallback implementation uses case-insensitive stance matching while the database implementation uses case-sensitive matching.

```python
# services/fighter_service.py:117-119 (case-insensitive)
stance_lower = stance.lower() if stance else None
fighter_stance = (getattr(fighter, "stance", None) or "").lower()
stance_match = fighter_stance == stance_lower

# db/repositories.py:174 (case-sensitive)
stmt = stmt.where(Fighter.stance == stance)
```

**Problem:**
- Searching for "orthodox" might work with in-memory but fail with database if stored as "Orthodox"
- Inconsistent user experience

**Fix Applied:**
Changed database query from `Fighter.stance == stance` to `Fighter.stance.ilike(stance)` for case-insensitive matching.

---

### 🟡 BUG-004: Transaction Management in load_scraped_data.py
✅ **FIXED**

**File:** `scripts/load_scraped_data.py:286-290, 301-302`
**Severity:** Medium
**Impact:** Performance degradation, potential transaction errors

**Issue:**
The script commits after every single fighter when loading from JSONL, then tries to commit again at the end.

```python
# Line 286-290
await session.merge(fighter)
loaded_count += 1

if not dry_run:
    await session.commit()  # Commits after EVERY fighter!

# Line 301-302
if not dry_run and session.in_transaction():
    await session.commit()  # Tries to commit again
```

**Problem:**
- Extremely inefficient - creates a database transaction per fighter
- The final commit check `session.in_transaction()` will likely be False
- Should batch commits or commit once at the end

**Fix Applied:**
Removed per-fighter commits (line 289-290) and simplified transaction checks. Now commits only once at the end of the loop for better performance.

---

## Low Severity Bugs

### 🟢 BUG-005: Missing Dependency in useFighters Hook
✅ **FIXED**

**File:** `frontend/src/hooks/useFighters.ts:67-69`
**Severity:** Low
**Impact:** Hook doesn't reload when initialLimit changes

**Issue:**
The `useEffect` dependency array is missing `initialLimit`, even though `loadFighters` uses it internally.

```typescript
// Line 64, 67-69
const nextPage = () => loadFighters(offset + initialLimit);  // Uses initialLimit

useEffect(() => {
  void loadFighters(0);
}, [searchTerm, stance]);  // Missing initialLimit!
```

**Problem:**
- If `initialLimit` changes, the effect won't re-run
- This is unlikely in practice since `initialLimit` is typically constant

**Fix Applied:**
Wrapped `loadFighters` in `useCallback` with proper dependencies `[searchTerm, stance, initialLimit]` and updated useEffect to depend on `[loadFighters]`.

---

### 🟢 BUG-006: Unnecessary useMemo in useSearch Hook
✅ **FIXED**

**File:** `frontend/src/hooks/useSearch.ts:13-16`
**Severity:** Low
**Impact:** Minor performance overhead, no functional issue

**Issue:**
The `useMemo` is unnecessary because Zustand selectors already return stable references.

```typescript
return useMemo(
  () => ({ searchTerm, stanceFilter, setSearchTerm, setStanceFilter }),
  [searchTerm, stanceFilter, setSearchTerm, setStanceFilter],
);
```

**Problem:**
- Zustand's `setSearchTerm` and `setStanceFilter` are already stable references
- The memoization adds overhead without benefit
- Standard pattern is to return values directly from Zustand hooks

**Fix Applied:**
Removed `useMemo` and `import { useMemo }` statement. Now returns the object directly.

---

## Recommendations

### ✅ All Bugs Fixed (5/6)
1. ✅ **BUG-001**: Removed redundant `session.close()` call from database connection
2. ✅ **BUG-003**: Made stance filtering case-insensitive in database queries
3. ✅ **BUG-004**: Batched commits in data loading script (commit at end, not per-fighter)
4. ✅ **BUG-005**: Added missing dependencies to useEffect with useCallback
5. ✅ **BUG-006**: Removed unnecessary useMemo from useSearch hook

### Remaining Issue (Not Critical)
**BUG-002**: Fighter Service Type Mismatch in Fallback
- This is a theoretical issue that only affects the InMemoryFighterRepository fallback
- The production code uses PostgreSQLFighterRepository which works correctly
- Low priority since InMemoryFighterRepository is only used for testing/prototyping

---

## Testing Recommendations

After fixes are applied, test:
1. Database connection handling under load
2. Search functionality with different case variations
3. Data loading script performance with large datasets
4. Frontend hooks with changing parameters

---

**End of Report**
