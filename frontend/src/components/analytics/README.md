# Fight Scatter Visualization

High-performance Canvas-based scatter plot visualization for UFC fight history analysis.

## Features

- **Dual-Canvas Architecture**: Heatmap layer + points layer for optimal rendering
- **Image-Based Markers**: Opponent headshots with color-coded borders (Win/Loss/Draw)
- **Interactive Zoom/Pan**: D3-powered smooth zoom and pan interactions
- **Trend Analysis**: Rolling median trend line computed in Web Worker
- **Density Heatmap**: Grid-based density visualization showing fight frequency
- **Smart Filtering**: Filter by result (W/L/D) and method (KO/SUB/DEC)
- **LRU Image Cache**: Off-thread image decoding with 256-entry cache
- **Rich Tooltips**: Detailed fight information on hover
- **Responsive**: Automatically adapts to container size

## Quick Start

### Basic Usage

```tsx
import { FightScatter } from "@/components/analytics/FightScatter";
import { convertFightToScatterPoint } from "@/lib/fight-scatter-utils";

const scatterFights = fightHistory.map(convertFightToScatterPoint);

<FightScatter
  fights={scatterFights}
  showTrend={true}
  onSelectFight={(id) => console.log("Selected:", id)}
/>
```

### Full-Featured Demo

```tsx
import { FightScatterDemo } from "@/components/analytics/FightScatterDemo";

<FightScatterDemo fightHistory={fighter.fight_history} />
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `fights` | `ScatterFight[]` | **required** | Array of fights to visualize |
| `hexbins` | `HexbinBucket[]` | `undefined` | Pre-computed density buckets |
| `domainY` | `[number, number]` | auto | Override Y-axis domain (seconds) |
| `showDensity` | `boolean` | `false` | Toggle density heatmap |
| `showTrend` | `boolean` | `false` | Toggle trend line |
| `filterResults` | `FightResult[]` | `[]` | Filter by W/L/D (empty = all) |
| `filterMethods` | `FightMethod[]` | `[]` | Filter by KO/SUB/DEC (empty = all) |
| `onSelectFight` | `(id: string) => void` | `undefined` | Callback on fight click |
| `className` | `string` | `""` | CSS class for container |
| `height` | `number` | `600` | Chart height in pixels |

## Data Preprocessing

Convert raw API data to scatter format:

```ts
import { convertFightToScatterPoint } from "@/lib/fight-scatter-utils";
import type { FightHistoryEntry } from "@/lib/types";

const fight: FightHistoryEntry = {
  fight_id: "fight1",
  event_name: "UFC 300",
  event_date: "2024-01-15",
  opponent: "John Doe",
  opponent_id: "opponent1",
  result: "W",
  method: "KO/TKO",
  round: 2,
  time: "3:45",
  // ...
};

const scatterPoint = convertFightToScatterPoint(fight);
// {
//   id: "fight1",
//   date: "2024-01-15",
//   finish_seconds: 525,  // Computed from round/time
//   method: "KO",
//   result: "W",
//   opponent_name: "John Doe",
//   headshot_url: "/img/opponents/opponent1-32.webp",
//   // ...
// }
```

## User Interactions

- **Zoom**: Scroll mouse wheel (0.5x to 5x zoom range)
- **Pan**: Click and drag
- **Hover**: Move mouse over markers to see tooltip
- **Click**: Click marker to select fight (fires `onSelectFight` callback)
- **Filter**: Non-matching fights fade to 15% opacity (not hidden)

## Performance

- Renders 500+ fights smoothly at 60 FPS
- Off-thread image decoding with `createImageBitmap()`
- LRU cache with automatic eviction (max 256 images)
- D3 quadtree for efficient spatial queries
- Web Worker for trend computation (non-blocking)

## Architecture

```
FightScatter.tsx
├── Heatmap Canvas (bottom layer)
│   └── Renders density grid with alpha gradient
├── Points Canvas (top layer)
│   ├── Renders opponent headshots as circular markers
│   ├── Color-coded borders by result
│   └── Method badge overlay
├── SVG Overlay (interaction layer)
│   ├── D3 zoom/pan behavior
│   └── Hit-testing with quadtree
└── Tooltip Portal
    └── Absolutely positioned fight details
```

## Files

### Components
- `FightScatter.tsx` - Main visualization component
- `FightTooltip.tsx` - Tooltip component
- `FightScatterDemo.tsx` - Full-featured demo with controls

### Utilities
- `fight-scatter-utils.ts` - Data preprocessing
- `imageCache.ts` - LRU image cache

### Workers
- `trendWorker.ts` - Rolling median computation

### Types
- `fight-scatter.ts` - TypeScript definitions

### Tests
- `fight-scatter-utils.test.ts` - Unit tests (18/18 passing)

## Testing

```bash
cd frontend
pnpm test run src/lib/__tests__/fight-scatter-utils.test.ts
```

## Example Integration

Add to fighter detail page:

```tsx
// frontend/app/fighters/[id]/page.tsx
import { FightScatterDemo } from "@/components/analytics/FightScatterDemo";

export default async function FighterPage({ params }) {
  const fighter = await getFighterDetail(params.id);

  return (
    <div>
      <FighterDetailCard fighter={fighter} />

      {fighter.fight_history.length > 0 && (
        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-bold">
            Fight History Analysis
          </h2>
          <FightScatterDemo fightHistory={fighter.fight_history} />
        </section>
      )}
    </div>
  );
}
```

## Future Enhancements

- WebGL rendering for 10,000+ fights
- LOWESS smoothing as alternative trend algorithm
- Export chart as PNG/SVG
- Keyboard navigation (arrow keys)
- Lasso selection for multi-fight analysis
- Animated transitions
- 3D visualization with Z-axis for additional metrics
