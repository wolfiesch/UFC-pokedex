# Fighter Card Fight Status Display

**Date:** 2025-01-11
**Status:** Ready for Implementation
**Priority:** Enhancement

## Summary

Add upcoming and recent fight status badges to fighter cards in their default state (before hover), making fight activity immediately visible without requiring user interaction.

## Design Decisions

### Visual Design
- **Location:** Compact stats row below fighter name (`record • stance • [BADGE]`)
- **Style:** Minimal icon + text, no background pills (subtle, doesn't compete with other badges)
- **Priority:** Show upcoming fight first, fallback to recent fight (last 30 days)
- **Icons:**
  - Upcoming: ⚔️ + date (e.g., "⚔️ Nov 15")
  - Recent Win: 🟢 + relative time (e.g., "🟢 8d ago")
  - Recent Loss: 🔴 + relative time (e.g., "🔴 8d ago")

### Data Strategy
- **Phase 1 (Minimal):** Add 3 computed fields to `FighterListItem`
  - `next_fight_date: date | None`
  - `last_fight_date: date | None` (already in DB, just expose it)
  - `last_fight_result: Literal["win", "loss", "draw", "nc"] | None`
- **Phase 2 (Future):** Optional rich fight objects via query param
  - `next_fight: FightHistoryEntry | None`
  - `last_fight: FightHistoryEntry | None`
  - Only when `?include_fight_details=true`

## Current State Analysis

### What Already Exists ✅
1. **Database Infrastructure:**
   - `fighters.last_fight_date` column (indexed, migration `1f9e5f49e8cc`)
   - `events.status` field ('upcoming' or 'completed')
   - `fights.event_id` links to events table
   - Upcoming fights marked with `fights.result = 'next'`

2. **Existing Patterns:**
   - `FavoriteUpcomingFight` schema in `backend/schemas/favorites.py`
   - `favorites_service.py` already queries upcoming fights using `result == "next"`
   - `_normalize_result()` helper: "next" → "upcoming"
   - Frontend shows "Next Fight" / "Last Fight" on hover (lines 441-451 in `EnhancedFighterCard.tsx`)

3. **Query Pattern Reference:**
   See `favorites_service.py` lines 521-531 for existing upcoming fight query logic.

### What's Missing ❌
1. Schema fields not exposed on `FighterListItem`
2. Repository query doesn't populate fight status data
3. Frontend doesn't display badges in default state

## Implementation Plan

### Phase 1: Backend Schema (1-2 hours)

**File:** `backend/schemas/fighter.py`

Add to `FighterListItem` (around line 53):
```python
# Lightweight fight status for default card display
next_fight_date: date | None = None
last_fight_date: date | None = None  # Already in DB, just expose it
last_fight_result: Literal["win", "loss", "draw", "nc"] | None = None
```

**No database migration needed** - we're using existing columns.

### Phase 2: Backend Repository (2-3 hours)

**File:** `backend/db/repositories/fighter_repository.py`

**Update `list_fighters()` method (starts at line 418):**

1. Add subquery for next upcoming fight:
```python
# Subquery: Get next fight date for each fighter
next_fight_subq = (
    select(
        Fight.fighter_id,
        func.min(Fight.event_date).label("next_fight_date")
    )
    .join(Event, Fight.event_id == Event.id)
    .where(Event.date > func.current_date())
    .where(Fight.result == "next")
    .group_by(Fight.fighter_id)
    .subquery()
)
```

2. Add subquery for last fight result:
```python
# Subquery: Get last fight result using existing last_fight_date
last_fight_subq = (
    select(
        Fight.fighter_id,
        Fight.result.label("last_result")
    )
    .where(
        Fight.event_date == Fighter.last_fight_date,
        Fight.fighter_id == Fighter.id
    )
    .limit(1)
    .subquery()
)
```

3. Update main query with LEFT JOINs:
```python
query = (
    select(Fighter)
    .options(load_only(*load_columns))
    .outerjoin(next_fight_subq, Fighter.id == next_fight_subq.c.fighter_id)
    .outerjoin(last_fight_subq, Fighter.id == last_fight_subq.c.fighter_id)
    .order_by(Fighter.last_fight_date.desc().nulls_last(), Fighter.name, Fighter.id)
)
```

4. Map fields in response construction (around line 499+):
```python
# Map next_fight_date from subquery
next_fight_date = getattr(fighter, 'next_fight_date', None)

# last_fight_date already exists on Fighter model
last_fight_date = fighter.last_fight_date

# Normalize last fight result using existing pattern
last_result_raw = getattr(fighter, 'last_result', None)
last_fight_result = self._normalize_fight_result(last_result_raw)
```

5. Add helper method (reuse favorites pattern):
```python
def _normalize_fight_result(self, result: str | None) -> Literal["win", "loss", "draw", "nc"] | None:
    """Normalize fight result to canonical form (reuses favorites_service pattern)."""
    if result is None:
        return None
    normalized = result.strip().lower()
    if normalized in {"w", "win"}:
        return "win"
    if normalized in {"l", "loss"}:
        return "loss"
    if normalized.startswith("draw"):
        return "draw"
    if normalized in {"nc", "no contest"}:
        return "nc"
    return None  # Ignore "next" and other values
```

**Update `search_fighters()` method similarly** - apply same subqueries and field mapping.

### Phase 3: Frontend Types (15 minutes)

**File:** `frontend/src/lib/types.ts`

Update `FighterListItem` type (around line 38):
```typescript
export type FighterListItem = {
  // ... existing fields ...

  // Fight status fields
  next_fight_date?: string | null;
  last_fight_date?: string | null;
  last_fight_result?: 'win' | 'loss' | 'draw' | 'nc' | null;
};
```

**Run:** `make types-generate` to regenerate OpenAPI types.

### Phase 4: Frontend Utilities (30 minutes)

**File:** `frontend/src/lib/fighter-utils.ts`

Add new utility function:
```typescript
/**
 * Format date as abbreviated month and day (e.g., "Nov 15")
 */
export function formatShortDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
```

Note: `getRelativeTime()` already exists and can be reused.

### Phase 5: Frontend Component (1-2 hours)

**File:** `frontend/src/components/fighter/EnhancedFighterCard.tsx`

**1. Add badge rendering helper (before component, around line 20):**
```typescript
interface FightBadgeProps {
  fighter: FighterListItem;
}

function FightBadge({ fighter }: FightBadgeProps): JSX.Element | null {
  const today = new Date();
  const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

  // Priority 1: Upcoming fight
  if (fighter.next_fight_date) {
    const nextDate = new Date(fighter.next_fight_date);
    if (nextDate > today) {
      return (
        <span className="flex items-center gap-1 text-muted-foreground">
          <span>⚔️</span>
          <span>{formatShortDate(nextDate)}</span>
        </span>
      );
    }
  }

  // Priority 2: Recent fight (last 30 days)
  if (fighter.last_fight_date && fighter.last_fight_result) {
    const lastDate = new Date(fighter.last_fight_date);
    if (lastDate >= thirtyDaysAgo && lastDate <= today) {
      const isWin = fighter.last_fight_result === 'win';
      const isLoss = fighter.last_fight_result === 'loss';

      if (isWin || isLoss) {
        return (
          <span className="flex items-center gap-1 text-muted-foreground">
            <span className={isWin ? 'text-green-500' : 'text-red-500'}>
              {isWin ? '🟢' : '🔴'}
            </span>
            <span>{getRelativeTime(fighter.last_fight_date)}</span>
          </span>
        );
      }
    }
  }

  return null;
}
```

**2. Update compact stats row (lines 512-515):**

Replace:
```typescript
<div className="flex items-center justify-between text-xs text-muted-foreground">
  <span>{fighter.record}</span>
  {fighter.stance && <span>{fighter.stance}</span>}
</div>
```

With:
```typescript
{/* Compact Stats Row with Fight Badge */}
<div className="flex items-center justify-between text-xs text-muted-foreground">
  <div className="flex items-center gap-2">
    <span>{fighter.record}</span>
    {fighter.stance && (
      <>
        <span>•</span>
        <span>{fighter.stance}</span>
      </>
    )}
    <FightBadge fighter={fighter} />
  </div>
</div>
```

**3. Add import:**
```typescript
import { formatShortDate, getRelativeTime } from "@/lib/fighter-utils";
```

### Phase 6: Testing (1 hour)

**Test Cases:**
1. ✅ Fighter with upcoming fight (Jack Della Maddalena - UFC 322 on Nov 15)
2. ✅ Fighter with recent win (check database for fights in last 30 days)
3. ✅ Fighter with recent loss (check database for fights in last 30 days)
4. ✅ Fighter with neither (older fighters)
5. ✅ Fighter with both (should prioritize upcoming over recent)
6. ✅ Mobile responsive (badge doesn't overflow)
7. ✅ Hover state still works (shows full details)

**Test Commands:**
```bash
# Start dev environment
make dev-local

# Test fighters with upcoming fights
curl "http://localhost:8000/fighters/?limit=50" | jq '.fighters[] | select(.next_fight_date != null)'

# Check specific fighter
curl "http://localhost:8000/fighters/6b453bc35a823c3f" | jq
```

## Performance Considerations

**Query Overhead:**
- +2 LEFT JOINs with subqueries
- Uses existing indexes:
  - `fighters.last_fight_date` (indexed)
  - `fights.event_date` (indexed)
  - `events.date` (indexed)
- Expected overhead: ~10-20ms per query
- Negligible compared to network latency (50-200ms typical)

**Caching Strategy:**
- List endpoint already cached by Redis (if available)
- Cache key includes query params
- TTL: 5 minutes (typical for roster lists)

## Rollback Plan

If performance issues arise:
1. Fields are optional (`| None`) - can return null without breaking frontend
2. No database migrations - just remove query joins
3. Frontend gracefully handles missing data (badge won't render)
4. Can add feature flag: `ENABLE_FIGHT_STATUS_BADGES=false`

## Future Enhancements (Phase 2)

**Rich fight details (opt-in):**
1. Add full fight objects to schema:
   ```python
   next_fight: FightHistoryEntry | None = None
   last_fight: FightHistoryEntry | None = None
   ```

2. Add query parameter:
   ```
   GET /fighters/?include_fight_details=true
   ```

3. Frontend can show opponent names:
   - Upcoming: "vs Makhachev Nov 15"
   - Recent: "W (KO) vs Kape 8d ago"

## References

- Existing pattern: `backend/services/favorites_service.py` lines 521-531
- Database migration: `1f9e5f49e8cc_add_last_fight_date_to_fighters.py`
- Frontend hover display: `EnhancedFighterCard.tsx` lines 441-451
- Result normalization: `favorites_service.py` line 608

## Success Metrics

- ✅ Users can see upcoming fights without hovering
- ✅ Users can see recent activity at a glance
- ✅ Query performance remains under 100ms p95
- ✅ Mobile display doesn't break or overflow
- ✅ Backwards compatible (no breaking changes)

---

**Estimated Total Time:** 6-9 hours
**Complexity:** Medium (leverages existing patterns)
**Risk:** Low (no schema changes, optional fields)
