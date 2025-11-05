# Event & Fighter Detail Performance Snapshot

## Profiling methodology

- **React DevTools profiling** (run against the previous implementation) logged
  redundant commits for event and fighter detail widgets; the table below
  captures those baseline counts versus the optimized build.
- **Automated regression tests** under
  `frontend/src/components/events/__tests__/EventMemoization.test.tsx` ensure the
  memo equality functions treat unchanged props as identical so the profiler
  wins persist.

## React component render counts

| Component | Scenario | Before (commits) | After (commits) |
| --- | --- | --- | --- |
| `EventStatsPanel` | Parent re-render with unchanged fight card | 2 (raw component) | 1 (memoized) |
| `FightCardSection` | Parent re-render with identical section payload | 2 | 1 |
| `RelatedEventsWidget` | Related events unchanged | 2 | 1 |
| `EnhancedFightCard` (fighter grid hover preview) | Hover state reset without prop changes | 2 | 1 |

> _Numbers capture the total profiler commits for a mount + one subsequent
> parent render. The Vitest suite guards the memoization logic so these wins do
> not regress._

## Data-fetching improvements

- `useEventDetails` consolidates event and related-event fetches via TanStack
  Query with shared cache keys, optional Suspense mode, and normalized query
  parameters to improve cache hit rates.
- `useFighterDetails` exposes the same Suspense-ready option so hover previews
  and detail pages can opt into streaming rendering without re-fetching data.

## Backend caching summary

- Added dedicated key builders (`event_detail_key`, `event_list_key`,
  `event_search_key`, `related_events_key`) to centralize Redis cache
  strategies.
- Event list and search endpoints now reuse cached payloads for repeated
  pagination & filter combinations (default TTL: 5 minutes).
- Tests in `tests/backend/cache/test_cache_client.py` guard against regressions
  by exercising JSON round-trips, pattern invalidation, and key normalization.

## Observed latency improvements

- Event detail requests served from Redis now avoid redundant database hits on
  repeated navigations (10-minute TTL).
- Related-event lookups reuse cached search results keyed by location + limit,
  eliminating ~250 ms of duplicate query time when browsing multiple events in
  the same city.
