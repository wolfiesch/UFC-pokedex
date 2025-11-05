# Fight Visualization Scatter Chart - Implementation Plan

**Created**: 2025-11-04
**Feature**: High-Performance Fight Scatter Visualization Component
**Status**: Planning

---

## 1. Overview

This plan outlines the implementation of a high-performance, Canvas-based scatter plot visualization that displays UFC fighter history over time. The component will plot fights by date and finish time, using opponent headshots as data points with color-coded borders indicating win/loss/draw outcomes. The visualization includes optional density heatmaps, trend lines, filtering, and zoom/pan interactions.

### Key Goals
- **Performance**: Render 500+ fights smoothly at 60 FPS with zoom/pan interactions
- **Visual Clarity**: Use opponent headshots instead of abstract dots for immediate recognition
- **Scalability**: Efficient image caching and lazy loading for hundreds of thumbnails
- **Interactivity**: Rich tooltips, filtering, and fight selection callbacks
- **Analytics**: Optional density overlays and trend lines for pattern analysis

---

## 2. Requirements and Goals

### Functional Requirements
1. **Data Visualization**
   - Plot fights on a 2D scatter chart (X-axis: date, Y-axis: finish time in seconds)
   - Display opponent headshots (32-48px WebP) as circular markers
   - Color-code borders by result: Win (#2ecc71), Loss (#e74c3c), Draw (#95a5a6)
   - Badge/glyph overlay showing finish method (KO, SUB, DEC, OTHER)

2. **Optional Overlays**
   - Density heatmap showing fight frequency over time (hexbin or grid-based)
   - Trend line showing finish time improvement (rolling-median or LOWESS)

3. **Interactivity**
   - Zoom/pan using d3-zoom
   - Hover tooltips with fight details (opponent, event, method, round:time)
   - Click to select fight (fires callback)
   - Filter by result (W/L/D) and method (KO/SUB/DEC)

4. **Performance**
   - LRU cache for decoded ImageBitmaps (max 256 entries)
   - Off-thread image decoding using `createImageBitmap()`
   - Preload visible + near-viewport images using `requestIdleCallback`
   - Batch canvas drawing operations
   - Keep JSON payload under 100 KB

### Non-Functional Requirements
- Smooth 60 FPS rendering during pan/zoom
- No layout shifts or jank
- Responsive container resizing
- TypeScript type safety throughout
- No third-party chart libraries (Canvas + D3 utilities only)

---

## 3. Technical Approach and Architecture

### Component Architecture

```
FightScatter.tsx (Main Component)
├── Canvas Layer Stack
│   ├── heatmapCanvas (bottom - density visualization)
│   └── pointsCanvas (top - fight markers)
├── Overlay Layer (SVG/div for hit-testing)
└── Tooltip Portal (absolute positioned)

Supporting Modules
├── utils/imageCache.ts (LRU cache for ImageBitmaps)
├── workers/trendWorker.ts (LOWESS/rolling-median computation)
├── scripts/gen-thumbnails.ts (Sharp-based thumbnail generator)
└── types/fight.ts (TypeScript type definitions)
```

### Data Flow

```
Backend Fight History API
    ↓
Data Preprocessing (convert finish time to seconds)
    ↓
Frontend Component (receives minimal JSON)
    ↓
Image Cache (preload opponent headshots)
    ↓
Canvas Rendering (stacked canvases with D3 scales)
    ↓
User Interaction (zoom/pan/hover/filter)
```

### Technology Stack
- **Rendering**: HTML5 Canvas API (dual-layer stack)
- **Scales/Transforms**: d3-scale, d3-zoom
- **Image Handling**: ImageBitmap API, LRU cache
- **Worker Thread**: Web Worker for trend computation
- **Build Tools**: Sharp (thumbnail generation)
- **Types**: TypeScript (strict mode)

---

## 4. Implementation Steps

### Phase 1: Type Definitions and Data Structure (Day 1)

**Task 1.1**: Create `frontend/src/types/fight.ts`
- [ ] Define `Fight` interface (id, date, finish_seconds, method, result, opponentId, headshotUrl)
- [ ] Define `FightScatterProps` interface
- [ ] Define `HexbinBucket` type
- [ ] Define `TrendPoint` type for worker communication
- [ ] Export method and result enums

**Task 1.2**: Extend backend schema (if needed)
- [ ] Review `backend/schemas/fighter.py` `FightHistoryEntry`
- [ ] Add computed `finish_seconds` field to response (or compute client-side)
- [ ] Add `opponent_image_url` or rely on opponent_id lookup
- [ ] Document finish time calculation rules (decisions = round_limit × 300)

**Task 1.3**: Create data preprocessing utility
- [ ] Create `frontend/src/lib/fight-scatter-utils.ts`
- [ ] Implement `convertFightToScatterPoint(fight: FightHistoryEntry): Fight`
  - Parse round/time string to total seconds
  - Handle decisions (3R = 900s, 5R = 1500s)
  - Map method strings to enum
- [ ] Implement `computeHexbins(fights: Fight[], bucketSize: number): HexbinBucket[]`
  - Grid-based density calculation
  - Return { i, j, count } buckets

### Phase 2: Image Cache System (Day 1-2)

**Task 2.1**: Implement `frontend/src/lib/utils/imageCache.ts`
- [ ] Create LRU cache class (max 256 entries)
- [ ] Implement `loadBitmap(url: string): Promise<ImageBitmap>`
  - Fetch blob
  - Decode with `createImageBitmap()` (off-thread)
  - Cache result
- [ ] Implement `getOpponentBitmap(opponentId: string, url: string): Promise<ImageBitmap>`
  - Check cache first
  - Return placeholder if loading/failed
- [ ] Implement `preloadBitmaps(urls: string[]): void`
  - Use `requestIdleCallback` for background loading
- [ ] Add cache eviction logic (LRU)

**Task 2.2**: Create placeholder fallback
- [ ] Generate in-memory colored circle canvas for missing images
- [ ] Cache placeholder as ImageBitmap
- [ ] Use fighter division color or generic gray

### Phase 3: Canvas Rendering Core (Day 2-3)

**Task 3.1**: Set up dual-canvas container in `frontend/src/components/analytics/FightScatter.tsx`
- [ ] Create responsive container div
- [ ] Create heatmapCanvas ref (bottom layer)
- [ ] Create pointsCanvas ref (top layer)
- [ ] Implement resize observer for container
- [ ] Set canvas dimensions with devicePixelRatio scaling

**Task 3.2**: Implement D3 scales
- [ ] Create `xScale = d3.scaleTime()` for date axis
- [ ] Create `yScale = d3.scaleLinear()` for finish_seconds
- [ ] Compute domains from data
- [ ] Apply padding to domains for better visual spacing

**Task 3.3**: Implement zoom/pan with d3-zoom
- [ ] Create zoom behavior instance
- [ ] Apply to overlay div/svg
- [ ] On zoom event, update transform state
- [ ] Trigger canvas redraw with new transform
- [ ] Clamp zoom extent (0.5x to 5x)

**Task 3.4**: Render fight markers on pointsCanvas
- [ ] Implement `renderFights(ctx, fights, xScale, yScale, transform, imageCache)`
- [ ] For each fight:
  - Compute screen position from scales + transform
  - Get cached ImageBitmap (or placeholder)
  - Draw circular clip path
  - Draw image inside circle
  - Draw colored border (2px, result-based color)
  - Draw method badge glyph in corner (small icon/text)
- [ ] Batch operations (minimize save/restore)
- [ ] Apply filter opacity (0.15 for non-matching filters)

**Task 3.5**: Render density heatmap on heatmapCanvas
- [ ] Implement `renderHexDensity(ctx, hexbins, xScale, yScale, transform)`
- [ ] For each hexbin:
  - Compute screen position
  - Draw hex/square with alpha = sqrt(count) / maxCount
  - Use gradient color ramp (cool → warm)
- [ ] Option: Pre-render to OffscreenCanvas for better performance
- [ ] Toggle visibility based on `showDensity` prop

### Phase 4: Interactivity (Day 3-4)

**Task 4.1**: Implement hit-testing with D3 quadtree
- [ ] Build quadtree from fight positions on data/transform change
- [ ] On pointer move, query quadtree for nearest node within radius
- [ ] Set `hoveredNodeId` state
- [ ] Highlight hovered fight (thicker border or glow effect)

**Task 4.2**: Implement tooltip
- [ ] Create `FightTooltip.tsx` component (portal-based)
- [ ] Position absolutely based on pointer coordinates
- [ ] Display:
  - Opponent name + headshot
  - Event name + date
  - Result + method
  - Round:time
  - Link to UFCStats fight card
- [ ] Update on hover state change
- [ ] Hide on pointer leave

**Task 4.3**: Implement click selection
- [ ] On pointer click, detect fight under cursor (quadtree)
- [ ] Call `onSelectFight(fightId)` callback
- [ ] Optional: Highlight selected fight with distinct visual (e.g., pulsing border)

**Task 4.4**: Implement filter UI
- [ ] Add toggle buttons for result filters (W/L/D)
- [ ] Add toggle buttons for method filters (KO/SUB/DEC/OTHER)
- [ ] On filter change, mark non-matching fights with low opacity (0.15)
- [ ] Do NOT remove from DOM (avoid re-layout)

### Phase 5: Density and Trend Features (Day 4-5)

**Task 5.1**: Implement trend line worker
- [ ] Create `frontend/src/workers/trendWorker.ts`
- [ ] Receive `{x: number, y: number}[]` array (sorted by x)
- [ ] Implement rolling-median smoothing:
  - Window size = 5-7 fights
  - Compute median finish_seconds for each window
- [ ] Alternative: LOWESS smoothing (if time permits)
- [ ] Return smoothed polyline points
- [ ] Handle edge cases (< window size fights)

**Task 5.2**: Integrate trend worker in main component
- [ ] Spawn worker on mount
- [ ] Send fight data on `showTrend` toggle or data change
- [ ] Listen for worker result
- [ ] Store trend points in state
- [ ] Render trend line on pointsCanvas (2px semi-transparent stroke)
- [ ] Draw after fight markers but before borders

**Task 5.3**: Add density/trend toggle controls
- [ ] Create toggle buttons in component header
- [ ] Update `showDensity` and `showTrend` state
- [ ] Re-render appropriate canvas layers

### Phase 6: Asset Optimization (Day 5)

**Task 6.1**: Create thumbnail generation script
- [ ] Create `frontend/scripts/gen-thumbnails.ts`
- [ ] Use Sharp library to batch process opponent images
- [ ] Input: Raw fighter images (e.g., `public/img/fighters/{id}.jpg`)
- [ ] Output: 32px WebP thumbnails to `public/img/opponents/{id}-32.webp`
- [ ] Optimize for quality/size balance (WebP quality: 80-85)
- [ ] Run script as part of build process (optional)

**Task 6.2**: Configure Next.js static serving
- [ ] Ensure `public/img/opponents/` is served with cache headers
- [ ] Set `Cache-Control: max-age=31536000, immutable` for WebP files
- [ ] Optional: Use Next.js Image Optimization API for dynamic serving

### Phase 7: Styling and UX Polish (Day 6)

**Task 7.1**: Define visual constants at top of component
```ts
const VISUAL_CONFIG = {
  MARKER_SIZE: 40,
  BORDER_WIDTH: 2,
  BADGE_SIZE: 12,
  COLORS: {
    WIN: '#2ecc71',
    LOSS: '#e74c3c',
    DRAW: '#95a5a6',
    TREND: 'rgba(52, 152, 219, 0.5)'
  },
  FILTER_OPACITY: 0.15,
  ZOOM_EXTENT: [0.5, 5] as [number, number],
  ANIMATION_DURATION: 200
};
```

**Task 7.2**: Implement responsive behavior
- [ ] On window resize, update canvas dimensions
- [ ] Maintain aspect ratio and scale
- [ ] Re-compute scales and redraw
- [ ] Debounce resize events (300ms)

**Task 7.3**: Add loading state
- [ ] Show skeleton/spinner during initial data fetch
- [ ] Show loading indicator when preloading images
- [ ] Disable interactions during loading

**Task 7.4**: Accessibility
- [ ] Add ARIA labels to canvas elements
- [ ] Keyboard navigation for fight selection (arrow keys + Enter)
- [ ] Screen reader announcements for filter changes
- [ ] Focus management for tooltip

### Phase 8: Testing and Optimization (Day 6-7)

**Task 8.1**: Performance testing
- [ ] Test with 500+ fights
- [ ] Measure FPS during pan/zoom (target: 60 FPS)
- [ ] Profile image loading times
- [ ] Monitor memory usage (image cache size)
- [ ] Test on low-end devices (throttle CPU in DevTools)

**Task 8.2**: Create unit tests
- [ ] Test data preprocessing utils (`convertFightToScatterPoint`)
- [ ] Test hexbin computation
- [ ] Test image cache LRU eviction
- [ ] Test filter logic

**Task 8.3**: Create integration tests (Playwright MCP)
- [ ] Test zoom/pan interactions
- [ ] Test hover tooltip appearance
- [ ] Test filter toggle behavior
- [ ] Test fight selection callback
- [ ] Test responsive resizing

**Task 8.4**: Optimization pass
- [ ] Minimize canvas save/restore calls (batch operations)
- [ ] Use OffscreenCanvas for pre-rendering static layers
- [ ] Debounce expensive operations (zoom, resize)
- [ ] Lazy-load trend worker (code splitting)

---

## 5. Files to Create or Modify

### New Files

#### Frontend Components
```
frontend/src/components/analytics/FightScatter.tsx
frontend/src/components/analytics/FightTooltip.tsx
frontend/src/components/analytics/__tests__/FightScatter.test.tsx
```

#### Utilities
```
frontend/src/lib/utils/imageCache.ts
frontend/src/lib/fight-scatter-utils.ts
frontend/src/lib/canvas-utils.ts (optional: shared canvas helpers)
```

#### Workers
```
frontend/src/workers/trendWorker.ts
```

#### Types
```
frontend/src/types/fight.ts (extend existing or create new)
```

#### Scripts
```
frontend/scripts/gen-thumbnails.ts
frontend/scripts/gen-thumbnails.sh (bash wrapper)
```

### Modified Files

#### Backend (if adding computed fields)
```
backend/schemas/fighter.py (add finish_seconds to FightHistoryEntry)
backend/services/fighter_service.py (compute finish_seconds)
backend/api/fighters.py (ensure opponent_id is included)
```

#### Frontend Types
```
frontend/src/lib/types.ts (extend FightHistoryEntry if needed)
```

#### Package Configuration
```
frontend/package.json (add Sharp dependency)
```

---

## 6. Dependencies and Prerequisites

### Existing Dependencies (Already Installed)
- `react` 18.3.1
- `next` 14.2.3
- `date-fns` 4.1.0 (for date parsing)
- `framer-motion` (optional: for animated transitions)

### New Dependencies to Install
```bash
cd frontend
pnpm add d3-scale d3-zoom d3-quadtree
pnpm add sharp --save-dev
```

### D3 Modules Needed
- `d3-scale`: Time and linear scales
- `d3-zoom`: Zoom/pan behavior
- `d3-quadtree`: Efficient spatial indexing for hit-testing

### Browser APIs Used
- Canvas API (2D rendering context)
- ImageBitmap API (off-thread image decoding)
- Web Workers API (trend computation)
- ResizeObserver API (responsive sizing)
- requestIdleCallback API (lazy image loading)

### Prerequisites
- Backend API must return fight history with:
  - `opponent_id` (for image lookup)
  - `round` and `time` (for finish_seconds calculation)
  - `result` (W/L/D)
  - `method` (KO/SUB/DEC/OTHER)
- Opponent headshot images available at `/img/opponents/{id}-32.webp`
- If images don't exist, component gracefully falls back to colored circles

---

## 7. Testing Strategy

### Unit Tests (Vitest)

**Test Suite 1: Data Preprocessing**
- Test `convertFightToScatterPoint()` with various round/time formats
- Test decision fight time calculation (3R vs 5R)
- Test method string normalization
- Test edge cases (missing data, malformed input)

**Test Suite 2: Image Cache**
- Test LRU eviction when exceeding max entries
- Test cache hits/misses
- Test concurrent image loading
- Test placeholder fallback

**Test Suite 3: Hexbin Computation**
- Test empty fight array
- Test single fight
- Test grid bucket assignment
- Test count aggregation

### Integration Tests (Playwright MCP)

**Test Case 1: Rendering**
- Navigate to fighter detail page with fight history
- Verify scatter chart appears
- Verify fight markers are visible
- Verify axes render correctly

**Test Case 2: Zoom/Pan**
- Scroll to zoom in/out
- Verify markers scale appropriately
- Drag to pan
- Verify markers reposition correctly

**Test Case 3: Hover Interaction**
- Move mouse over fight marker
- Verify tooltip appears
- Verify tooltip content matches fight data
- Move mouse away, verify tooltip disappears

**Test Case 4: Filtering**
- Click "Loss" filter toggle
- Verify loss markers fade to 15% opacity
- Click "KO" filter toggle
- Verify only KO wins remain at full opacity
- Clear filters, verify all markers return to full opacity

**Test Case 5: Density/Trend Toggle**
- Click "Show Density" toggle
- Verify heatmap appears on background
- Click "Show Trend" toggle
- Verify trend line appears
- Disable toggles, verify layers disappear

### Performance Tests

**Benchmark 1: Render Performance**
- Load fighter with 500+ fights
- Measure time to first paint
- Target: < 500ms

**Benchmark 2: Interaction Performance**
- Measure FPS during continuous pan
- Target: 60 FPS

**Benchmark 3: Image Loading**
- Measure time to load all visible images
- Target: < 2s for 50 images

**Benchmark 4: Memory Usage**
- Monitor heap size with 500+ fights loaded
- Verify image cache stays within limit (256 entries)
- Check for memory leaks on component unmount

---

## 8. Potential Challenges and Edge Cases

### Challenge 1: Image Loading Performance
**Problem**: Loading 500+ opponent headshots could cause network congestion and slow initial render.

**Solutions**:
- Preload only visible images first (viewport priority)
- Use `requestIdleCallback` for background loading of off-screen images
- Implement progressive loading (load low-quality placeholders first)
- Cache aggressively with service worker (if applicable)
- Consider sprite sheets for very large datasets (future optimization)

### Challenge 2: Canvas Redraw Performance
**Problem**: Redrawing 500+ images on every pan/zoom frame could drop FPS below 60.

**Solutions**:
- Use OffscreenCanvas for static layers (density heatmap)
- Implement viewport culling (only draw visible fights)
- Batch canvas operations (minimize save/restore)
- Use transform matrix instead of translating each point
- Consider WebGL rendering for 1000+ points (future)

### Challenge 3: Touch Device Interactions
**Problem**: Touch devices need pinch-to-zoom and different event handling.

**Solutions**:
- d3-zoom handles touch events natively
- Test on iPad/mobile devices
- Adjust marker size for touch targets (min 44px)
- Add touch-specific UI hints

### Challenge 4: Finish Time Data Inconsistency
**Problem**: Different fight types (3R, 5R, title fights) have different max durations. Decisions don't have a "finish_seconds" value.

**Solutions**:
- Normalize decisions to max fight time (3R = 900s, 5R = 1500s)
- Document assumption clearly in code comments
- Add tooltip note for decision fights ("Full Time")
- Consider separate visual treatment for decisions (square markers instead of circles)

### Challenge 5: Missing Opponent Images
**Problem**: Not all opponents may have headshots available.

**Solutions**:
- Fallback to colored circle placeholder (division color or gray)
- Pre-generate placeholder ImageBitmap on mount
- Add visual indicator (initials overlay) if name available
- Consider fetching default UFC silhouette image

### Challenge 6: Date Range Gaps
**Problem**: Fighters with long career gaps create sparse visualizations.

**Solutions**:
- Auto-adjust X-axis domain to active period
- Add "zoom to fit" button
- Option to toggle between absolute dates and relative career timeline
- Show career breaks with visual separator line

### Challenge 7: Overlapping Markers
**Problem**: Multiple fights on same date or similar finish times create overlap.

**Solutions**:
- Implement force-based jitter (slight random offset)
- Add transparency/stacking order
- Zoom in to see overlapped markers
- Hover shows count of overlapping fights

### Challenge 8: Accessibility
**Problem**: Canvas is not inherently accessible to screen readers.

**Solutions**:
- Add hidden table with same data for screen readers
- Implement keyboard navigation (Tab to cycle through fights)
- ARIA live region for announcing hover/selection
- Provide text export option

---

## 9. Success Criteria

### Performance Metrics
✅ Renders 500+ fights in < 500ms (initial paint)
✅ Maintains 60 FPS during pan/zoom
✅ Image cache stays within 256 entry limit
✅ Payload size < 100 KB for 500 fights
✅ First meaningful paint < 1s on 3G connection

### Functional Criteria
✅ All fight markers display with correct colors and borders
✅ Opponent headshots load and display correctly
✅ Tooltip shows accurate fight details on hover
✅ Zoom/pan interactions work smoothly
✅ Filters apply correctly (result and method)
✅ Density heatmap toggles on/off
✅ Trend line displays and updates correctly
✅ Click selection fires callback with correct fight ID

### UX Criteria
✅ Responsive container resizes without breaking layout
✅ Loading states provide clear feedback
✅ Fallback placeholders appear for missing images
✅ Keyboard navigation works (arrow keys + Enter)
✅ Touch interactions work on mobile/tablet
✅ Accessible to screen readers (ARIA annotations)

### Code Quality Criteria
✅ Full TypeScript type coverage (no `any` types)
✅ All components have unit tests (>80% coverage)
✅ Integration tests cover main user flows
✅ No console errors or warnings
✅ ESLint and Prettier pass
✅ Code documented with JSDoc comments

---

## 10. Implementation Timeline

### Week 1
**Day 1**: Type definitions, data preprocessing, image cache foundation
**Day 2**: Canvas setup, D3 scales, basic rendering
**Day 3**: Zoom/pan, hover interactions, quadtree hit-testing

### Week 2
**Day 4**: Tooltip implementation, filtering, density heatmap
**Day 5**: Trend worker, trend line rendering, asset optimization
**Day 6**: UX polish, responsive behavior, accessibility
**Day 7**: Testing, optimization, documentation

### Total Effort
**Estimated**: 7 days (1 developer, full-time)
**Realistic**: 10-14 days (accounting for iterations and bug fixes)

---

## 11. Future Enhancements (Out of Scope)

- WebGL rendering for 10,000+ fights
- Animated transitions between filter states
- Lasso selection for multi-fight analysis
- Export chart as PNG/SVG
- Comparative overlay (multiple fighters on same chart)
- Time-lapse animation showing career progression
- Integration with event timeline (click fight → jump to event detail)
- Heatmap of win/loss distribution by division/year
- 3D visualization (add Z-axis for striking accuracy or opponent ranking)

---

## 12. References and Resources

### Documentation
- [Canvas API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API)
- [ImageBitmap API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/ImageBitmap)
- [d3-scale Documentation](https://d3js.org/d3-scale)
- [d3-zoom Documentation](https://d3js.org/d3-zoom)
- [Web Workers (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API)
- [Sharp Documentation](https://sharp.pixelplumbing.com/)

### Existing Codebase References
- `frontend/src/components/FightWeb/FightGraphCanvas.tsx` (canvas + D3 zoom example)
- `frontend/src/lib/types.ts` (FightHistoryEntry type)
- `backend/schemas/fighter.py` (FightHistoryEntry schema)
- `frontend/src/components/visualizations/FightHistoryTimeline.tsx` (timeline visualization pattern)

### Similar Implementations
- FightGraphCanvas.tsx uses dual-layer rendering (SVG + Canvas)
- Image loading patterns from FighterImagePlaceholder.tsx

---

## 13. Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Poor performance with 500+ fights | High | Medium | Implement viewport culling, OffscreenCanvas, lazy loading |
| Missing opponent images | Medium | High | Robust placeholder fallback, pre-generate missing thumbnails |
| Browser compatibility (ImageBitmap) | Medium | Low | Polyfill or fallback to regular Image API for older browsers |
| D3-zoom conflicts with other interactions | Medium | Medium | Careful event delegation, pointer capture management |
| Trend calculation too slow | Low | Low | Move to Web Worker (already planned) |
| Memory leaks from image cache | High | Medium | Proper cleanup on unmount, LRU eviction |

---

## 14. Open Questions

1. **Data Source**: Should finish_seconds be computed backend or frontend?
   - **Recommendation**: Backend (single source of truth, reduces frontend complexity)

2. **Image Format**: WebP vs AVIF for opponent headshots?
   - **Recommendation**: WebP (better browser support, Sharp supports it)

3. **Trend Algorithm**: Rolling-median vs LOWESS?
   - **Recommendation**: Start with rolling-median (simpler), add LOWESS if needed

4. **Density Algorithm**: Hexbin vs grid?
   - **Recommendation**: Grid (simpler to implement, similar visual effect)

5. **Default View**: Zoom to fit all fights or show recent fights?
   - **Recommendation**: Recent 2 years at full detail, with "Zoom to fit" button

6. **Method Badges**: Icons vs text abbreviations?
   - **Recommendation**: Text abbreviations (KO, SUB, DEC) - simpler, no asset dependencies

---

## 15. Appendix: Component API

### Props

```typescript
interface FightScatterProps {
  // Required
  fights: Fight[];

  // Optional data
  hexbins?: HexbinBucket[];
  domainY?: [number, number];

  // Feature toggles
  showDensity?: boolean;
  showTrend?: boolean;

  // Filters
  filterResults?: ('W' | 'L' | 'D')[];
  filterMethods?: ('KO' | 'SUB' | 'DEC' | 'OTHER')[];

  // Callbacks
  onSelectFight?: (fightId: string) => void;

  // Styling
  className?: string;
  height?: number;
}
```

### Example Usage

```tsx
import { FightScatter } from '@/components/analytics/FightScatter';
import { useFighterFights } from '@/hooks/useFighterFights';

export function FighterAnalyticsPage({ fighterId }: { fighterId: string }) {
  const { fights, isLoading } = useFighterFights(fighterId);
  const [showDensity, setShowDensity] = useState(false);
  const [showTrend, setShowTrend] = useState(true);
  const [filterResults, setFilterResults] = useState<('W' | 'L' | 'D')[]>(['W', 'L', 'D']);

  const handleSelectFight = (fightId: string) => {
    console.log('Selected fight:', fightId);
    // Navigate to fight detail or show modal
  };

  if (isLoading) return <div>Loading...</div>;

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <button onClick={() => setShowDensity(!showDensity)}>
          {showDensity ? 'Hide' : 'Show'} Density
        </button>
        <button onClick={() => setShowTrend(!showTrend)}>
          {showTrend ? 'Hide' : 'Show'} Trend
        </button>
      </div>

      <FightScatter
        fights={fights}
        showDensity={showDensity}
        showTrend={showTrend}
        filterResults={filterResults}
        onSelectFight={handleSelectFight}
        height={600}
      />
    </div>
  );
}
```

---

**End of Plan**
