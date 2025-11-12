# Last 5 Fights Visualization - Planning Document

**Date**: 2025-01-12
**Status**: Planning
**Priority**: Enhancement

## Overview

Add a visual representation of a fighter's last 5 fight results using colored circles (red for losses, green for wins) displayed on the fighter card. This provides an at-a-glance view of recent performance beyond just the current streak.

## Current State Analysis

### Streak Data Available
- **Current streaks in database**: 2-6 fights (min: 2, max: 6)
- **Longest streaks**: GSP, Khabib, Jon Jones, Ilia Topuria, Pantoja (all 6-fight win streaks)
- **Data already computed**: `current_streak_type` and `current_streak_count` in fighters table
- **Limitation**: Current implementation only shows streak length, not the actual fight-by-fight breakdown

### Fight History Data
- **Available**: Complete fight history with results in `FighterDetail` API response
- **Format**: Array of `FightHistoryEntry` with `result` field (values: "win", "loss", "draw", "nc", "next")
- **Issue**: Fight history is only fetched on hover (lazy loaded for performance)

## Design Goals

1. **Visual Clarity**: Instantly show recent performance trend
2. **Minimal Space**: Fit within existing compact stats row
3. **Performance**: Don't slow down initial page load
4. **Consistency**: Match existing design system (green for wins, red for losses)

## Design Options

### Option A: Last 5 Fights Circles (Recommended)
Display 5 small circles showing the last 5 completed fights, left-to-right (oldest to newest).

**Visual**:
```
17-8-0 • Flyweight • [🟢🟢🔴🟢🔴]
```

**Pros**:
- Clear historical view beyond current streak
- Shows patterns (e.g., alternating wins/losses vs consistent performance)
- Familiar pattern (similar to GitHub contribution graph)

**Cons**:
- Requires fight history data (not available in list endpoint)
- Adds horizontal space to compact row

### Option B: Streak Bar
Show current streak as a horizontal colored bar with length proportional to streak count.

**Visual**:
```
17-8-0 • Flyweight • ████ 4W
```

**Pros**:
- Uses existing streak data (no new API calls)
- Emphasizes momentum

**Cons**:
- Doesn't show fight-by-fight breakdown
- Less informative than Option A

### Option C: Hybrid Approach
Show circles for last 5 fights, with current streak highlighted.

**Visual**:
```
17-8-0 • Flyweight • 🔴🔴[🟢🟢🟢]
```
(brackets around streak)

**Pros**:
- Combines historical view with streak emphasis
- Most informative option

**Cons**:
- More complex implementation
- Requires careful visual design to avoid clutter

## Recommended Approach: Option A

Show last 5 completed fights as colored circles.

### Visual Design

**Colors**:
- 🟢 Green circle: Win
- 🔴 Red circle: Loss
- ⚪ Gray circle: Draw
- ⚫ Dark gray circle: No Contest

**Size**: 8px diameter circles with 2px gap
**Positioning**: After division in compact stats row
**Order**: Left to right = oldest to newest (chronological)

### Layout Integration

**Before**:
```
17-8-0 • Flyweight • 🟢 2 • ⚔️ Dec 13
```

**After**:
```
17-8-0 • Flyweight • [●●●○○] • ⚔️ Dec 13
```
(where ● = filled circle, ○ = outline for upcoming)

**Alternative (if space is tight)**:
Move to its own row below compact stats:
```
17-8-0 • Flyweight • ⚔️ Dec 13
[🟢🟢🔴🟢🟢] Last 5 fights
```

## Technical Implementation

### Phase 1: Backend Changes

**1. Add `last_5_results` field to `FighterListItem` schema**
```python
# backend/schemas/fighter.py
class FighterListItem(BaseModel):
    # ... existing fields ...
    last_5_results: list[Literal["win", "loss", "draw", "nc"]] = Field(default_factory=list)
```

**2. Compute last 5 results in repository**
```python
# backend/db/repositories/fighter_repository.py
async def _fetch_last_5_results(
    self, fighter_ids: Sequence[str]
) -> dict[str, list[Literal["win", "loss", "draw", "nc"]]]:
    """Fetch last 5 completed fight results for given fighters."""
    # Query fights table, filter by result != 'next'
    # Order by event_date DESC
    # Limit 5 per fighter
    # Return dict mapping fighter_id to list of results
```

**3. Update list_fighters() and search_fighters()**
- Call `_fetch_last_5_results()`
- Populate `last_5_results` field in FighterListItem

**4. Add query parameter (optional)**
```python
# backend/api/fighters.py
include_last_5: bool = Query(
    False,
    description="Include last 5 fight results in list payload"
)
```

### Phase 2: Frontend Changes

**1. Create `LastFightCircles` component**
```tsx
// frontend/src/components/fighter/LastFightCircles.tsx
interface LastFightCirclesProps {
  results: ("win" | "loss" | "draw" | "nc")[];
}

function LastFightCircles({ results }: LastFightCirclesProps) {
  if (!results || results.length === 0) return null;

  return (
    <div className="flex items-center gap-0.5" title="Last 5 fights">
      {results.slice(-5).map((result, idx) => (
        <div
          key={idx}
          className={cn(
            "w-2 h-2 rounded-full",
            result === "win" ? "bg-green-500" :
            result === "loss" ? "bg-red-500" :
            result === "draw" ? "bg-gray-400" :
            "bg-gray-600"
          )}
        />
      ))}
    </div>
  );
}
```

**2. Update API calls**
```typescript
// frontend/src/lib/api.ts
include_last_5: true,  // Add to both getFighters() and searchFighters()
```

**3. Update EnhancedFighterCard compact stats row**
```tsx
{/* Compact Stats Row with All Badges */}
<div className="flex items-center gap-2 flex-wrap">
  <span className="font-medium">{fighter.record}</span>

  {fighter.division && (
    <>
      <span>•</span>
      <span>{fighter.division}</span>
    </>
  )}

  {/* Last 5 Fights Circles */}
  {fighter.last_5_results && fighter.last_5_results.length > 0 && (
    <>
      <span>•</span>
      <LastFightCircles results={fighter.last_5_results} />
    </>
  )}

  {/* Win Streak Badge (maybe remove since last 5 shows this?) */}
  {/* ... */}

  {/* Fight Status Badge */}
  <FightBadge fighter={fighter} />
</div>
```

**4. Regenerate TypeScript types**
```bash
npx openapi-typescript http://localhost:8000/openapi.json -o frontend/src/lib/generated/api-schema.ts
```

## Data Considerations

### Performance Impact
- **Additional DB query**: 1 query with 5-row limit per fighter (minimal overhead)
- **Payload size**: ~5 bytes per fighter (5 single-char results)
- **Caching**: Leverages existing Redis cache infrastructure

### Data Quality
- **Streaks stored in DB**: Only 39% of fighters (1814/4600)
- **Fight history available**: For all fighters with fights
- **Need to filter**: Exclude "next" and other non-result values

### Edge Cases
1. **Fighters with < 5 fights**: Show only available fights
2. **No completed fights**: Show nothing (or "Debut")
3. **Very old fighters**: Last 5 might be years old
4. **Upcoming fight in last 5**: Exclude from count

## Alternative: Use Existing Streak Data

If we want to avoid the backend changes, we could **visualize the current streak** using circles:

```tsx
// Show streak as repeated circles
function StreakCircles({ type, count }: { type: "win" | "loss", count: number }) {
  const circles = Math.min(count, 5); // Cap at 5 for display
  const color = type === "win" ? "bg-green-500" : "bg-red-500";

  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: circles }).map((_, idx) => (
        <div key={idx} className={`w-2 h-2 rounded-full ${color}`} />
      ))}
      {count > 5 && <span className="text-xs ml-1">+{count - 5}</span>}
    </div>
  );
}
```

**Pros**: No backend changes, uses existing data
**Cons**: Less informative (doesn't show fight-by-fight breakdown)

## Open Questions

1. **Should we remove the current streak badge** if we show last 5 fights? (Last 5 implicitly shows streak)
2. **Should we show opponent names on hover** over each circle?
3. **Should circles be clickable** to navigate to fight details?
4. **What if a fighter has mixed results** (e.g., 🟢🔴🟢🔴🟢)? Still valuable to show?
5. **Should we show dates** on hover (e.g., "Win vs. Kape - Dec 2024")?

## Decision Required

**Before implementing**, we need to decide:

1. ✅ **Option A** (Last 5 fights) vs **Option B** (Streak bar) vs **Simplified approach** (visualize existing streak)
2. Keep or remove current streak badge text (e.g., "🟢 2")?
3. Backend implementation: Always compute or only when `include_last_5=true`?
4. Visual design: Circles inline vs separate row?

## Recommendation

**Start with simplified approach** using existing streak data:
1. Convert current streak text badge to visual circles
2. Keep the same data (no backend changes)
3. Iterate based on user feedback

Example:
```
Before: 17-8-0 • Flyweight • 🟢 3 • ⚔️ Dec 13
After:  17-8-0 • Flyweight • 🟢🟢🟢 • ⚔️ Dec 13
```

**Then expand to full last-5 implementation** if visual approach tests well.

## Success Metrics

- User can instantly understand recent fighter performance trend
- No significant performance degradation on page load
- Visual design is clear and not cluttered
- Matches existing design system aesthetic

---

**Next Steps**: Decide on approach, then proceed with implementation.

**Current Date/Time:** 01/12/2025 12:55 AM
