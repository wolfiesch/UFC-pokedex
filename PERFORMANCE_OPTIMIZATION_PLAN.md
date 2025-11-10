# UFC Pokedex - Performance Optimization Plan

**Generated**: November 10, 2025 at 1:55 AM
**Tool**: Ceviz v0.0.3 Performance Analysis
**Scope**: Frontend codebase (Next.js + React + TypeScript)

---

## Executive Summary

Ceviz performance analysis identified **128 performance issues** across **127 files** in the frontend codebase:

- **Critical Issues**: 114 (O(n²) complexity, memory leaks, blocking operations)
- **Warnings**: 14 (potential optimizations, best practices)
- **Performance Score**: 0/100 ❌
- **Analysis Time**: 104ms

### Impact Assessment

The critical issues can severely impact user experience at scale:
- O(n²) loops: **100ms → 10s** for 1000 items
- O(n*m) array operations: **10ms → 5s** for 1000x1000 items
- Memory leaks: Accumulating memory usage over time
- Sequential async requests: Waterfall delays

---

## Critical Issues Breakdown

### 1. **Algorithmic Complexity (O(n²) & O(n*m))**
**Priority**: 🔴 CRITICAL
**Impact**: High - Performance degradation at scale
**Count**: ~100+ issues

#### Affected Files
1. **`next.config.mjs`** (lines 122-123)
   - Array.filter() inside loop during webpack config
   - Impact: Development build performance

2. **`src/workers/trendWorker.ts`** (line 44)
   - Nested loop in rolling median calculation
   - Impact: Chart rendering delays

3. **`src/lib/utils.ts`** (line 19)
   - Array operations in getInitials function
   - Impact: Fighter card rendering

4. **`src/lib/format.ts`** (line 32)
   - Nested loop in toTitleCase helper
   - Impact: Label formatting across UI

5. **`src/store/favoritesStore.ts`** (lines 216, 304)
   - Array.filter() inside loops in state updates
   - Nested loop in getFavorites()
   - Impact: Favorites management performance

#### Recommended Fixes
- **Pre-compute lookups**: Convert arrays to `Map`/`Set` before loops
- **Use hash-based structures**: Replace `array.find()` in loops with `map.get()`
- **Memoization**: Cache expensive computations
- **Batch operations**: Group array mutations

### 2. **Memory Leaks**
**Priority**: 🔴 CRITICAL
**Impact**: High - Memory accumulation over time
**Count**: 4 identified

#### Common Patterns
- Event listeners not cleaned up in useEffect
- Web Workers not terminated properly
- Zustand subscriptions without cleanup
- Timer/interval references not cleared

#### Recommended Fixes
- Add cleanup functions to all useEffect hooks
- Implement proper Worker.terminate() calls
- Unsubscribe from Zustand stores in cleanup
- Use AbortController for fetch requests

### 3. **Sequential Async Operations (Waterfalls)**
**Priority**: 🟡 HIGH
**Impact**: Medium - Increased latency
**Count**: 14 identified

#### Common Patterns
- Sequential API calls that could be parallel
- Await chains without Promise.all()
- Dependent requests that could be batched

#### Recommended Fixes
```typescript
// ❌ Before (Sequential)
const fighters = await fetchFighters();
const stats = await fetchStats();
const events = await fetchEvents();

// ✅ After (Parallel)
const [fighters, stats, events] = await Promise.all([
  fetchFighters(),
  fetchStats(),
  fetchEvents(),
]);
```

---

## Implementation Plan

### Phase 1: Quick Wins (Week 1)
**Goal**: Fix highest-impact issues with minimal refactoring

#### 1.1 Fix Critical O(n²) Loops
- [x] **next.config.mjs** (lines 122-123) - Convert to Set *(confirmed existing config already merges ignore lists via `Set`, no regression work required)*
  - Estimated time: 15 minutes
  - Impact: Faster dev builds

- [x] **trendWorker.ts** (line 44) - Optimize rolling median *(implemented sliding-window median with dual heaps)*
  - Estimated time: 1 hour
  - Impact: Smooth chart rendering

- [x] **favoritesStore.ts** (lines 216, 304) - Use Map for lookups *(store now maintains `Set`/`Map` + cached favorites list)*
  - Estimated time: 2 hours
  - Impact: Faster favorites management

#### 1.2 Add Memory Leak Cleanup
- [x] Audit all useEffect hooks for cleanup *(worker listeners cleaned up, command palette fetch now abortable)*
  - Estimated time: 3 hours
  - Impact: Prevent memory growth

- [x] Add Worker termination to trendWorker usage *(FightScatter tears down worker + listener explicitly)*
  - Estimated time: 30 minutes
  - Impact: Prevent worker memory leaks

#### 1.3 Parallelize Independent API Calls
- [x] Audit all async/await chains *(no additional independent chains found; documented findings and ensured cancellable search requests)*
  - Estimated time: 2 hours
  - Impact: Reduce page load times

**Total Phase 1 Time**: ~9 hours
**Expected Performance Improvement**: 30-40%

### Phase 2: Structural Optimizations (Week 2)
**Goal**: Address systemic performance patterns

#### 2.1 Implement Memoization Strategy
- [ ] Wrap expensive utils in `useMemo`
  - `getColorFromString()` - Memoize hash calculations
  - `formatMetricLabel()` - Memoize label transformations
  - `toTitleCase()` - Cache converted strings

- [ ] Add React.memo to pure components
  - Fighter cards
  - Stats displays
  - Chart components

#### 2.2 Optimize State Management
- [ ] Review Zustand selectors for unnecessary re-renders
- [ ] Implement shallow equality checks
- [ ] Split large stores into smaller, focused stores

#### 2.3 Code Splitting & Lazy Loading
- [ ] Lazy load chart components (Recharts)
- [ ] Dynamic imports for heavy visualizations
- [ ] Route-based code splitting

**Total Phase 2 Time**: ~15 hours
**Expected Performance Improvement**: Additional 20-30%

### Phase 3: Advanced Optimizations (Week 3)
**Goal**: Achieve production-ready performance

#### 3.1 Implement Virtual Scrolling
- [ ] Fighter grid virtualization (react-window)
- [ ] Large table virtualization
- [ ] Infinite scroll for events timeline

#### 3.2 Web Worker Optimization
- [ ] Move heavy computations to workers
  - Fighter filtering/sorting
  - Stats calculations
  - Graph layout algorithms

#### 3.3 Caching Strategy
- [ ] Implement SWR (Stale-While-Revalidate)
- [ ] Add Redis caching layer (backend)
- [ ] Browser cache optimization

#### 3.4 Bundle Optimization
- [ ] Analyze bundle size with webpack-bundle-analyzer
- [ ] Tree-shake unused dependencies
- [ ] Replace heavy libraries with lighter alternatives

**Total Phase 3 Time**: ~20 hours
**Expected Performance Improvement**: Additional 20-30%

---

## Detailed Fix Guide

### Fix #1: next.config.mjs Array.filter() in Loop

**Status**: ✅ Already optimized

**Notes**:
- The current config already normalises the watch ignore list and merges it via `new Set([...normalizedIgnored, ...IGNORED_WATCH_PATTERNS])`, so duplicates are removed without nested loops.
- Documented this so future changes do not reintroduce redundant filtering work.

**Testing**:
- `pnpm dev` hot reloads continue to ignore repo-root assets correctly.

---

### Fix #2: trendWorker.ts Nested Loop

**File**: `frontend/src/workers/trendWorker.ts`
**Status**: ✅ Completed

**What changed**:
- Replaced the `points.slice(...).map(...)` hot path with a proper sliding-window median that keeps two heaps (max + min) in sync, using lazy deletions to support O(log k) inserts/removals.
- Added a lightweight heap implementation plus a `SlidingMedian` helper so each iteration only adds/removes at most one value as the window advances.
- The worker now processes N points in O(n log k) time (k = window size) instead of re-sorting every window, eliminating stutters when 1k+ points are plotted.

```typescript
const slidingMedian = new SlidingMedian();
while (currentEnd < targetEnd) {
  slidingMedian.add(yValues[currentEnd]);
  currentEnd += 1;
}
while (currentStart < targetStart) {
  slidingMedian.remove(yValues[currentStart]);
  currentStart += 1;
}
const medianY = slidingMedian.getMedian(targetEnd - targetStart);
smoothed.push({ x: points[i].x, y: medianY });
```

**Testing**:
- Manual verification in Fight Scatter confirms the trend overlay now renders almost instantly even with large datasets.

---

### Fix #3: favoritesStore.ts Array Operations

**File**: `frontend/src/store/favoritesStore.ts`
**Status**: ✅ Completed

**What changed**:
- Added a `deriveFavoritesSnapshot` helper that materialises `favoriteIds: Set<string>`, `favoriteEntryMap: Map<string, FavoriteEntry>` and a memoised `favoriteListCache` whenever the collection changes.
- `isFavorite` now performs O(1) `Set.has` checks, toggle flows reuse the `Map` to fetch the relevant entry, and `getFavorites` simply returns the cached list instead of mapping/filtering every time.
- Optimistic updates reuse the helper so Zustand subscribers receive consistent references (no manual set cloning scattered throughout the store).

```typescript
function deriveFavoritesSnapshot(collection: FavoriteCollectionDetail | null) {
  const favoriteIds = new Set<string>();
  const favoriteEntryMap = new Map<string, FavoriteEntry>();
  const favoriteListCache: FighterListItem[] = [];
  // ...
  return { defaultCollection: collection, favoriteIds, favoriteEntryMap, favoriteListCache };
}
```

**Testing**:
- Toggled favorites via UI to confirm instant updates and correct backend sync (`_refreshCollection` still runs after optimistic writes).

---

### Fix #4: Memory Leak - Web Worker Cleanup

**Status**: ✅ Completed

**Changes made**:
- `FightScatter` now stores the `message` handler, removes it on teardown, terminates the worker, and nulls the ref to prevent dangling listeners when the component remounts.
- The command palette search effect now wraps fetches in an `AbortController`, cancels the pending timeout + request on dependency changes, and ensures `isLoading` resets when searches are cleared—preventing background promises from updating unmounted state.

**Testing**:
- Verified via React DevTools that remounting the Fight Scatter page no longer spawns multiple workers.
- Repeatedly typing/clearing the command palette query no longer logs fetch errors or leaves `isLoading` stuck.

---

### Fix #5: Waterfall Async Calls

**Status**: ✅ Audited

**Findings**:
- Favorites initialization still requires `getFavoriteCollections` to resolve before knowing which collection to hydrate, so there are no safe opportunities for `Promise.all` there. Documented the dependency to avoid future regressions.
- Other frontend data loaders already issue requests in parallel (React Query takes care of caching + batched prefetching).
- The command palette search is inherently single-request but now cancels in-flight calls when the query changes, preventing waterfall behaviour across quick keystrokes.

---

## Performance Monitoring

### Metrics to Track

#### Before Optimization Baseline
- [ ] Lighthouse Performance Score (Desktop): ____
- [ ] Lighthouse Performance Score (Mobile): ____
- [ ] First Contentful Paint (FCP): ____
- [ ] Largest Contentful Paint (LCP): ____
- [ ] Time to Interactive (TTI): ____
- [ ] Total Blocking Time (TBT): ____
- [ ] Cumulative Layout Shift (CLS): ____

#### After Each Phase
Track same metrics and document improvements in this file.

### Tools
- **Chrome DevTools Performance Tab**: Profile runtime performance
- **React DevTools Profiler**: Identify unnecessary re-renders
- **Lighthouse**: Overall performance score
- **webpack-bundle-analyzer**: Bundle size optimization
- **Ceviz**: Re-run after each phase to track issue reduction

### Testing Strategy
1. **Unit Tests**: Verify optimized functions produce same output
2. **Integration Tests**: Ensure optimizations don't break features
3. **Performance Tests**: Benchmark before/after
4. **Visual Regression**: Ensure UI unchanged
5. **Load Testing**: Test with large datasets (1000+ fighters)

---

## Risk Assessment

### Low Risk (Safe to Implement)
- ✅ Converting arrays to Sets/Maps for lookups
- ✅ Adding useEffect cleanup functions
- ✅ Parallelizing independent API calls
- ✅ Memoization of pure functions

### Medium Risk (Requires Testing)
- ⚠️ Changing Zustand state structure
- ⚠️ Implementing virtual scrolling
- ⚠️ Web Worker refactoring

### High Risk (Requires Careful Review)
- ⛔ Major algorithm rewrites (rolling median)
- ⛔ State management refactoring
- ⛔ Bundle splitting changes

---

## Success Criteria

### Phase 1 Success
- ✅ Ceviz critical issues reduced from 114 → <50
- ✅ Performance score improved from 0 → 40+
- ✅ No memory leaks detected in Chrome DevTools
- ✅ All existing tests pass

### Phase 2 Success
- ✅ Ceviz critical issues reduced to <20
- ✅ Performance score 60+
- ✅ Lighthouse mobile score 80+
- ✅ LCP < 2.5s on 3G connection

### Phase 3 Success
- ✅ Ceviz critical issues = 0
- ✅ Performance score 80+
- ✅ Lighthouse mobile score 90+
- ✅ Handles 10,000+ fighters without lag

---

## Resources

### Documentation
- [Ceviz GitHub](https://github.com/productdevbook/ceviz)
- [React Performance Optimization](https://react.dev/learn/render-and-commit)
- [Web.dev Performance](https://web.dev/learn-web-vitals/)

### Tools
- [Ceviz Report](frontend/ceviz-report.html) - Interactive HTML report
- [React DevTools Profiler](https://react.dev/learn/react-developer-tools)
- [Chrome DevTools Performance](https://developer.chrome.com/docs/devtools/performance/)

### Code References
- Repository pattern: `backend/db/repositories.py`
- State management: `frontend/src/store/favoritesStore.ts`
- API client: `frontend/src/lib/api-client.ts`

---

## Appendix: Full Issue Statistics

### Issues by Category
- **Nested Loops (O(n²))**: ~60 issues
- **Array Operations in Loops (O(n*m))**: ~40 issues
- **Memory Leaks**: 4 issues
- **Sequential Async (Waterfalls)**: 14 issues
- **Other Warnings**: 10 issues

### Files with Most Issues
(Top 15 files to prioritize)
1. **Components**: Fighter cards, event cards, filters
2. **State Management**: Zustand stores
3. **Utilities**: Format, utils, fight-utils
4. **Visualizations**: Charts, graphs, timelines
5. **Config**: next.config.mjs, webpack config

### Estimated Total Effort
- **Phase 1** (Quick Wins): ~9 hours
- **Phase 2** (Structural): ~15 hours
- **Phase 3** (Advanced): ~20 hours
- **Testing & QA**: ~10 hours
- **Total**: ~54 hours (≈7 working days)

---

**Last Updated**: November 10, 2025 at 1:55 AM
**Status**: Phase 1 Complete
**Next Action**: Kick off Phase 2 structural optimizations
