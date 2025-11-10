# FightMatrix Historical Rankings Frontend Integration

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete frontend interface for viewing FightMatrix historical rankings including division leaderboards, fighter ranking history charts, and peak ranking displays.

**Architecture:** Next.js 14 App Router pages consuming the existing rankings API (`/rankings/*`) endpoints. Uses the type-safe API client for all backend communication. Implements Server-Side Rendering (SSR) for the main rankings page and client-side components for interactive charts using Recharts.

**Tech Stack:** Next.js 14, React, TypeScript, Tailwind CSS, Recharts, openapi-fetch, Sonner (toasts)

---

## Task 1: Regenerate TypeScript Types from OpenAPI Schema

The API already exposes rankings endpoints, but the frontend TypeScript types need to be regenerated to include the new ranking schemas.

**Files:**
- Check: `frontend/src/lib/generated/api-schema.ts` (auto-generated, will be updated)
- Check: Backend must be running at `http://localhost:8000`

**Step 1: Verify backend is running**

Run: `ps aux | grep uvicorn | grep 8000`
Expected: Process running on port 8000

If not running:
```bash
cd /Users/wolfgangschoenberger/Projects/UFC-pokedex
make api
```

Wait for: "Application startup complete" message

**Step 2: Regenerate TypeScript types**

Run: `make types-generate`

Expected output:
- "Fetching OpenAPI schema from http://localhost:8000/openapi.json..."
- "Generating TypeScript types..."
- "✔ Types generated successfully"

**Step 3: Verify ranking types exist**

Run: `grep -A 5 "RankingEntry\|CurrentRankingsResponse\|RankingHistoryResponse" frontend/src/lib/generated/api-schema.ts`

Expected: Type definitions for `RankingEntry`, `CurrentRankingsResponse`, `RankingHistoryResponse`, `PeakRankingResponse`

**Step 4: Commit**

```bash
git add frontend/src/lib/generated/api-schema.ts
git commit -m "feat: regenerate TypeScript types for rankings API

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Create Rankings Page Server Component

Create the main `/rankings` page that displays current rankings for all divisions.

**Files:**
- Create: `frontend/app/rankings/page.tsx`

**Step 1: Write the failing test (N/A - testing covered by browser verification)**

No unit test for this SSR page component. We'll verify visually in browser.

**Step 2: Create rankings page component**

Create: `frontend/app/rankings/page.tsx`

```typescript
import type { Metadata } from "next";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import client from "@/lib/api-client";

export const metadata: Metadata = {
  title: "Rankings • UFC Fighter Pokedex",
  description: "View current UFC fighter rankings across all weight classes from FightMatrix.",
};

// Force dynamic rendering to get fresh rankings data
export const dynamic = 'force-dynamic';

export default async function RankingsPage() {
  // Fetch all current rankings from FightMatrix
  const { data, error } = await client.GET("/rankings/", {
    params: {
      query: { source: "fightmatrix" }
    }
  });

  if (error || !data) {
    return (
      <section className="container flex flex-col gap-12 py-12">
        <header className="space-y-4">
          <Badge variant="outline" className="w-fit tracking-[0.35em]">
            Rankings
          </Badge>
          <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
            Fighter Rankings
          </h1>
        </header>
        <div
          className="rounded-3xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive-foreground"
          role="alert"
        >
          Failed to load rankings data. Please try again later.
        </div>
      </section>
    );
  }

  const { divisions, division_rank_dates, total_fighters } = data;

  return (
    <section className="container flex flex-col gap-12 py-12">
      <header className="space-y-4">
        <Badge variant="outline" className="w-fit tracking-[0.35em]">
          Rankings
        </Badge>
        <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
          Fighter Rankings
        </h1>
        <p className="max-w-2xl text-lg text-muted-foreground">
          Current UFC fighter rankings across all weight classes from FightMatrix historical data.
        </p>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>Total Fighters: {total_fighters}</span>
          <span>•</span>
          <span>Source: FightMatrix</span>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        {divisions.map((division) => {
          const dateInfo = division_rank_dates.find(d => d.division === division.division);

          return (
            <Card key={division.division}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>{division.division}</span>
                  {division.total_fighters > 0 && (
                    <Badge variant="outline" className="text-xs">
                      {division.total_fighters} fighters
                    </Badge>
                  )}
                </CardTitle>
                {dateInfo && (
                  <CardDescription>
                    Updated: {new Date(dateInfo.rank_date).toLocaleDateString()}
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent>
                {division.rankings.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No rankings available for this division.
                  </p>
                ) : (
                  <ol className="space-y-2">
                    {division.rankings.slice(0, 5).map((entry) => (
                      <li
                        key={entry.ranking_id}
                        className="flex items-center justify-between text-sm"
                      >
                        <Link
                          href={`/fighters/${entry.fighter_id}`}
                          className="flex items-center gap-3 hover:underline"
                        >
                          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs font-semibold">
                            {entry.rank === 0 ? "C" : entry.rank ?? "NR"}
                          </span>
                          <span className="font-medium">{entry.fighter_name}</span>
                          {entry.nickname && (
                            <span className="text-muted-foreground">
                              &ldquo;{entry.nickname}&rdquo;
                            </span>
                          )}
                        </Link>
                        {entry.rank_movement !== 0 && (
                          <Badge
                            variant={entry.rank_movement > 0 ? "default" : "destructive"}
                            className="text-xs"
                          >
                            {entry.rank_movement > 0 ? "↑" : "↓"}
                            {Math.abs(entry.rank_movement)}
                          </Badge>
                        )}
                      </li>
                    ))}
                  </ol>
                )}
                {division.rankings.length > 5 && (
                  <Link
                    href={`/rankings/${encodeURIComponent(division.division)}`}
                    className="mt-4 block text-sm font-medium text-primary hover:underline"
                  >
                    View all {division.total_fighters} fighters →
                  </Link>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
```

**Step 3: Verify page exists**

Run: `ls -la frontend/app/rankings/page.tsx`

Expected: File exists with ~150 lines

**Step 4: Commit**

```bash
git add frontend/app/rankings/page.tsx
git commit -m "feat: add rankings overview page with all divisions

- Server-side render rankings from FightMatrix API
- Show top 5 fighters per division
- Link to detailed division pages
- Display rank movement indicators

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: Create Division-Specific Rankings Page

Create a dynamic route for viewing complete rankings for a single division.

**Files:**
- Create: `frontend/app/rankings/[division]/page.tsx`

**Step 1: Create division rankings page**

Create: `frontend/app/rankings/[division]/page.tsx`

```typescript
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import client from "@/lib/api-client";

type DivisionRankingsPageProps = {
  params: {
    division: string;
  };
};

export async function generateMetadata({
  params,
}: DivisionRankingsPageProps): Promise<Metadata> {
  const division = decodeURIComponent(params.division);

  return {
    title: `${division} Rankings • UFC Fighter Pokedex`,
    description: `View complete ${division} fighter rankings from FightMatrix.`,
  };
}

// Force dynamic rendering for fresh data
export const dynamic = 'force-dynamic';

export default async function DivisionRankingsPage({
  params,
}: DivisionRankingsPageProps) {
  const division = decodeURIComponent(params.division);

  const { data, error } = await client.GET("/rankings/{division}", {
    params: {
      path: { division },
      query: { source: "fightmatrix" }
    }
  });

  if (error || !data) {
    notFound();
  }

  const { rankings, rank_date, total_fighters } = data;

  // Separate champion from ranked fighters
  const champion = rankings.find(r => r.rank === 0);
  const rankedFighters = rankings.filter(r => r.rank !== null && r.rank > 0).sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0));
  const unrankedFighters = rankings.filter(r => r.rank === null);

  return (
    <section className="container flex flex-col gap-8 py-12">
      {/* Header */}
      <header className="space-y-4">
        <Link
          href="/rankings"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          ← Back to all rankings
        </Link>
        <Badge variant="outline" className="w-fit tracking-[0.35em]">
          Rankings
        </Badge>
        <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
          {division}
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>Updated: {new Date(rank_date).toLocaleDateString()}</span>
          <span>•</span>
          <span>{total_fighters} fighters</span>
          <span>•</span>
          <span>Source: FightMatrix</span>
        </div>
      </header>

      {/* Champion */}
      {champion && (
        <Card className="bg-gradient-to-br from-yellow-500/10 to-amber-500/10 border-yellow-500/30">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-yellow-500 to-amber-600 text-2xl font-bold text-white shadow-lg">
                C
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <Badge className="bg-gradient-to-r from-yellow-500 to-amber-600 text-white border-0">
                    {champion.is_interim ? "INTERIM CHAMPION" : "CHAMPION"}
                  </Badge>
                </div>
                <Link
                  href={`/fighters/${champion.fighter_id}`}
                  className="text-2xl font-semibold hover:underline"
                >
                  {champion.fighter_name}
                </Link>
                {champion.nickname && (
                  <p className="text-sm text-muted-foreground">
                    &ldquo;{champion.nickname}&rdquo;
                  </p>
                )}
              </div>
              {champion.rank_movement !== 0 && (
                <Badge
                  variant={champion.rank_movement > 0 ? "default" : "destructive"}
                  className="text-sm"
                >
                  {champion.rank_movement > 0 ? "↑" : "↓"}
                  {Math.abs(champion.rank_movement)}
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Ranked Fighters */}
      {rankedFighters.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold tracking-tight">Top 15</h2>
          <Card>
            <CardContent className="p-0">
              <ol className="divide-y">
                {rankedFighters.map((entry) => (
                  <li
                    key={entry.ranking_id}
                    className="flex items-center justify-between gap-4 p-4 hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-center gap-4 flex-1 min-w-0">
                      <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-muted text-sm font-semibold">
                        {entry.rank}
                      </span>
                      <div className="flex-1 min-w-0">
                        <Link
                          href={`/fighters/${entry.fighter_id}`}
                          className="font-medium hover:underline block truncate"
                        >
                          {entry.fighter_name}
                        </Link>
                        {entry.nickname && (
                          <p className="text-sm text-muted-foreground truncate">
                            &ldquo;{entry.nickname}&rdquo;
                          </p>
                        )}
                      </div>
                    </div>
                    {entry.rank_movement !== 0 && (
                      <Badge
                        variant={entry.rank_movement > 0 ? "default" : "destructive"}
                        className="text-xs flex-shrink-0"
                      >
                        {entry.rank_movement > 0 ? "↑" : "↓"}
                        {Math.abs(entry.rank_movement)}
                      </Badge>
                    )}
                    {entry.rank_movement === 0 && entry.previous_rank !== null && (
                      <Badge variant="outline" className="text-xs flex-shrink-0">
                        —
                      </Badge>
                    )}
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Unranked Fighters (if any) */}
      {unrankedFighters.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold tracking-tight">Not Ranked (NR)</h2>
          <Card>
            <CardContent className="p-0">
              <ul className="divide-y">
                {unrankedFighters.map((entry) => (
                  <li
                    key={entry.ranking_id}
                    className="flex items-center gap-4 p-4 hover:bg-muted/50 transition-colors"
                  >
                    <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted-foreground">
                      NR
                    </span>
                    <div className="flex-1 min-w-0">
                      <Link
                        href={`/fighters/${entry.fighter_id}`}
                        className="font-medium hover:underline block truncate"
                      >
                        {entry.fighter_name}
                      </Link>
                      {entry.nickname && (
                        <p className="text-sm text-muted-foreground truncate">
                          &ldquo;{entry.nickname}&rdquo;
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      )}
    </section>
  );
}
```

**Step 2: Verify page exists**

Run: `ls -la frontend/app/rankings/[division]/page.tsx`

Expected: File exists

**Step 3: Commit**

```bash
git add frontend/app/rankings/[division]/page.tsx
git commit -m "feat: add division-specific rankings page

- Display complete fighter list for a division
- Highlight champion with special styling
- Show rank movement indicators
- Separate ranked vs unranked fighters

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: Create Ranking History Chart Component

Build a client component to display a fighter's ranking history over time using Recharts.

**Files:**
- Create: `frontend/src/components/rankings/RankingHistoryChart.tsx`

**Step 1: Create ranking history chart component**

Create: `frontend/src/components/rankings/RankingHistoryChart.tsx`

```typescript
"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type RankingDataPoint = {
  ranking_id: string;
  division: string;
  rank: number | null;
  previous_rank: number | null;
  rank_movement: number;
  is_interim: boolean;
  rank_date: string;
  source: string;
};

type RankingHistoryChartProps = {
  fighterName: string;
  history: RankingDataPoint[];
  division?: string;
};

export default function RankingHistoryChart({
  fighterName,
  history,
  division,
}: RankingHistoryChartProps) {
  // Transform data for Recharts (reverse to show oldest first, left to right)
  const chartData = useMemo(() => {
    return [...history]
      .reverse()
      .map((entry) => ({
        date: new Date(entry.rank_date).toLocaleDateString("en-US", {
          month: "short",
          year: "numeric",
        }),
        rank: entry.rank ?? null,
        division: entry.division,
        isChamp: entry.rank === 0,
        isInterim: entry.is_interim,
      }));
  }, [history]);

  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Ranking History</CardTitle>
          <CardDescription>
            {division ? `${division} Division` : "All Divisions"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No ranking history available for this fighter.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Custom tooltip to show rank details
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="rounded-lg border bg-background p-3 shadow-md">
          <p className="font-semibold">{data.date}</p>
          <p className="text-sm">
            Division: {data.division}
          </p>
          <p className="text-sm font-semibold">
            Rank: {data.isChamp ? (data.isInterim ? "Champion (I)" : "Champion") : data.rank ?? "NR"}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Ranking History</CardTitle>
        <CardDescription>
          {division ? `${division} Division` : "All Divisions"} • {chartData.length} snapshots
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              className="text-muted-foreground"
            />
            <YAxis
              reversed
              domain={[0, 15]}
              ticks={[0, 1, 5, 10, 15]}
              tickFormatter={(value) => (value === 0 ? "C" : value.toString())}
              tick={{ fontSize: 12 }}
              label={{ value: "Rank", angle: -90, position: "insideLeft" }}
              className="text-muted-foreground"
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Line
              type="monotone"
              dataKey="rank"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={{ fill: "hsl(var(--primary))", r: 4 }}
              activeDot={{ r: 6 }}
              name="Rank"
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
        <p className="mt-4 text-xs text-muted-foreground">
          Lower rank number = higher position. Champion = 0. NR = Not Ranked.
        </p>
      </CardContent>
    </Card>
  );
}
```

**Step 2: Verify component exists**

Run: `ls -la frontend/src/components/rankings/RankingHistoryChart.tsx`

Expected: File exists

**Step 3: Commit**

```bash
git add frontend/src/components/rankings/RankingHistoryChart.tsx
git commit -m "feat: add ranking history chart component

- Line chart showing rank progression over time
- Custom tooltip with division and rank details
- Reversed Y-axis (champion at top)
- Handles missing data (NR periods)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: Create Peak Ranking Display Component

Build a component to highlight a fighter's peak ranking achievement.

**Files:**
- Create: `frontend/src/components/rankings/PeakRanking.tsx`

**Step 1: Create peak ranking component**

Create: `frontend/src/components/rankings/PeakRanking.tsx`

```typescript
"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type PeakRankingProps = {
  fighterName: string;
  division: string;
  peakRank: number;
  rankDate: string;
  isInterim: boolean;
  source: string;
};

export default function PeakRanking({
  fighterName,
  division,
  peakRank,
  rankDate,
  isInterim,
  source,
}: PeakRankingProps) {
  const isChampion = peakRank === 0;
  const formattedDate = new Date(rankDate).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return (
    <Card className={isChampion ? "bg-gradient-to-br from-yellow-500/10 to-amber-500/10 border-yellow-500/30" : ""}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <svg
            className="h-5 w-5 text-yellow-500"
            fill="currentColor"
            viewBox="0 0 20 20"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
          Peak Ranking
        </CardTitle>
        <CardDescription>{division}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-baseline gap-2">
          <span className="text-5xl font-bold">
            {isChampion ? "C" : `#${peakRank}`}
          </span>
          {isChampion && (
            <Badge className="bg-gradient-to-r from-yellow-500 to-amber-600 text-white border-0">
              {isInterim ? "INTERIM CHAMPION" : "CHAMPION"}
            </Badge>
          )}
        </div>
        <div className="space-y-1 text-sm text-muted-foreground">
          <p>Achieved: {formattedDate}</p>
          <p>Source: {source.toUpperCase()}</p>
        </div>
        {isChampion && (
          <p className="text-sm font-medium text-foreground">
            {fighterName} reached the pinnacle of the {division} division.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
```

**Step 2: Verify component exists**

Run: `ls -la frontend/src/components/rankings/PeakRanking.tsx`

Expected: File exists

**Step 3: Commit**

```bash
git add frontend/src/components/rankings/PeakRanking.tsx
git commit -m "feat: add peak ranking display component

- Highlight fighter's best ranking achievement
- Special styling for championship peak
- Show date and division
- Trophy icon for visual emphasis

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: Add Ranking History to Fighter Detail Page

Integrate the ranking history chart and peak ranking into the existing fighter detail page.

**Files:**
- Modify: `frontend/src/components/Pokedex/FighterDetailPageClient.tsx`

**Step 1: Read current fighter detail client component**

Run: `head -100 frontend/src/components/Pokedex/FighterDetailPageClient.tsx`

Expected: Client component with fighter data, fight history, etc.

**Step 2: Add ranking data fetching**

Modify: `frontend/src/components/Pokedex/FighterDetailPageClient.tsx`

Add imports at top:
```typescript
import RankingHistoryChart from "@/components/rankings/RankingHistoryChart";
import PeakRanking from "@/components/rankings/PeakRanking";
```

Add state and fetching logic inside the component (after existing state declarations):
```typescript
const [rankingHistory, setRankingHistory] = useState<any>(null);
const [peakRanking, setPeakRanking] = useState<any>(null);
const [rankingsLoading, setRankingsLoading] = useState(true);

// Fetch ranking data
useEffect(() => {
  async function fetchRankings() {
    try {
      setRankingsLoading(true);

      // Fetch history and peak in parallel
      const [historyRes, peakRes] = await Promise.all([
        client.GET("/rankings/fighter/{fighter_id}/history", {
          params: {
            path: { fighter_id: fighter.fighter_id },
            query: { source: "fightmatrix", limit: 50 }
          }
        }),
        client.GET("/rankings/fighter/{fighter_id}/peak", {
          params: {
            path: { fighter_id: fighter.fighter_id },
            query: { source: "fightmatrix" }
          }
        })
      ]);

      if (historyRes.data && historyRes.data.history.length > 0) {
        setRankingHistory(historyRes.data);
      }

      if (peakRes.data) {
        setPeakRanking(peakRes.data);
      }
    } catch (error) {
      console.error("Failed to fetch rankings:", error);
    } finally {
      setRankingsLoading(false);
    }
  }

  fetchRankings();
}, [fighter.fighter_id]);
```

Add ranking section to the JSX (after fight history section, before closing container):
```typescript
{/* Rankings Section */}
{!rankingsLoading && (rankingHistory || peakRanking) && (
  <section className="space-y-6">
    <h2 className="text-3xl font-semibold tracking-tight">Rankings</h2>
    <div className="grid gap-6 lg:grid-cols-2">
      {peakRanking && (
        <PeakRanking
          fighterName={fighter.name}
          division={peakRanking.division}
          peakRank={peakRanking.peak_rank}
          rankDate={peakRanking.rank_date}
          isInterim={peakRanking.is_interim}
          source={peakRanking.source}
        />
      )}
      {rankingHistory && rankingHistory.history.length > 0 && (
        <div className="lg:col-span-2">
          <RankingHistoryChart
            fighterName={fighter.name}
            history={rankingHistory.history}
          />
        </div>
      )}
    </div>
  </section>
)}
```

**Step 3: Verify the changes compile**

Run: `cd frontend && npx tsc --noEmit`

Expected: No type errors

**Step 4: Commit**

```bash
git add frontend/src/components/Pokedex/FighterDetailPageClient.tsx
git commit -m "feat: integrate rankings into fighter detail page

- Fetch ranking history and peak rank on mount
- Display peak ranking card
- Show ranking history chart
- Handle loading states and missing data

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 7: Add Rankings Navigation Link

Add a link to the rankings page in the site header navigation.

**Files:**
- Modify: `frontend/src/components/layout/site-header.tsx`

**Step 1: Read current site header**

Run: `cat frontend/src/components/layout/site-header.tsx | head -80`

Expected: Header component with navigation links

**Step 2: Add rankings link to navigation**

Modify: `frontend/src/components/layout/site-header.tsx`

Find the navigation links section and add:
```typescript
<Link
  href="/rankings"
  className="text-sm font-medium transition-colors hover:text-primary"
>
  Rankings
</Link>
```

Place it between "Stats" and "Fight Web" or after "Events" (wherever makes sense in the existing nav structure).

**Step 3: Verify file compiles**

Run: `cd frontend && npx tsc --noEmit`

Expected: No type errors

**Step 4: Commit**

```bash
git add frontend/src/components/layout/site-header.tsx
git commit -m "feat: add rankings link to site navigation

- Add Rankings menu item to header
- Position between existing nav links

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 8: Manual Testing & Verification

Verify the complete rankings feature works end-to-end.

**Step 1: Start the development servers**

Run: `make dev-local`

Expected:
- Backend starts on port 8000
- Frontend starts on port 3000

**Step 2: Visit rankings overview page**

Open browser: `http://localhost:3000/rankings`

Verify:
- ✅ Page loads without errors
- ✅ Divisions are displayed in grid layout
- ✅ Each division shows top 5 fighters
- ✅ Rank movement indicators appear (↑↓)
- ✅ "View all fighters →" link present
- ✅ Updated date displayed

**Step 3: Click on a division**

Click: "Lightweight" (or any division with data)

Verify:
- ✅ Division detail page loads
- ✅ Champion displayed with special styling
- ✅ Top 15 ranked fighters shown
- ✅ Rank movement badges visible
- ✅ Fighter links navigate to detail pages
- ✅ "Back to all rankings" link works

**Step 4: Visit fighter detail page**

Navigate to any fighter with ranking history (e.g., search for a known champion)

Verify:
- ✅ Rankings section appears below fight history
- ✅ Peak Ranking card displays correctly
- ✅ Ranking History chart renders
- ✅ Chart shows timeline with proper axis labels
- ✅ Tooltip works when hovering over data points
- ✅ No console errors

**Step 5: Test error states**

1. Stop the backend server
2. Refresh rankings page
3. Verify: Error message displays gracefully

Run: `pkill -f uvicorn`
Refresh: `http://localhost:3000/rankings`
Expected: "Failed to load rankings data" message

**Step 6: Restart servers and test responsiveness**

Run: `make dev-local`

Test on mobile viewport:
- Resize browser to 375px width
- Verify: Rankings grid becomes single column
- Verify: Chart is responsive
- Verify: Navigation works on mobile

**Step 7: Check for TypeScript errors**

Run: `cd frontend && npx tsc --noEmit`

Expected: 0 errors

**Step 8: Check for linting errors**

Run: `cd frontend && pnpm run lint`

Expected: No errors or warnings

---

## Task 9: Final Integration Testing

Test the complete user journey.

**Step 1: User flow test - Homepage to Rankings**

1. Visit: `http://localhost:3000`
2. Click: "Rankings" in header
3. Select: "Welterweight" division
4. Click: A fighter's name
5. Scroll: To rankings section
6. Verify: All data loads correctly

**Step 2: Test data consistency**

Open terminal and check:
```bash
curl -s http://localhost:8000/rankings/?source=fightmatrix | python3 -m json.tool | head -50
```

Expected: Valid JSON response with divisions array

**Step 3: Performance check**

In browser DevTools Network tab:
- Reload `/rankings` page
- Verify: Page loads in < 2 seconds
- Check: No unnecessary API calls
- Verify: Images load progressively

**Step 4: Accessibility check**

Run in browser console:
```javascript
// Check for proper heading hierarchy
document.querySelectorAll('h1, h2, h3').forEach(h => console.log(h.tagName, h.textContent));
```

Expected: Proper h1 → h2 → h3 hierarchy

**Step 5: Document completion**

Create a brief summary of what was implemented:
- ✅ Rankings overview page (`/rankings`)
- ✅ Division detail pages (`/rankings/[division]`)
- ✅ Ranking history chart component
- ✅ Peak ranking display component
- ✅ Fighter detail page integration
- ✅ Navigation link added

---

## Task 10: Create Pull Request (Optional)

If working in a feature branch, create a PR.

**Step 1: Check git status**

Run: `git status`

Expected: All changes committed

**Step 2: Push to remote**

Run: `git push origin HEAD`

Expected: Branch pushed successfully

**Step 3: Create PR** (if configured)

Run: `gh pr create --title "feat: FightMatrix rankings frontend integration" --body "$(cat <<'EOF'
## Summary
Complete frontend integration for FightMatrix historical rankings feature.

## Changes
- ✅ Rankings overview page showing all divisions
- ✅ Division-specific detailed ranking pages
- ✅ Interactive ranking history chart (Recharts)
- ✅ Peak ranking achievement display
- ✅ Integration into fighter detail pages
- ✅ Navigation menu updated

## Testing
- [x] Manual testing completed
- [x] TypeScript compilation passes
- [x] Linting passes
- [x] Responsive design verified
- [x] Error states handled

## Screenshots
(Add screenshots from manual testing)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"`

Expected: PR created successfully

---

## Notes for Future Maintenance

**Type Safety Chain:**
1. Backend Pydantic models (`backend/schemas/ranking.py`)
2. OpenAPI schema generation (`/openapi.json`)
3. TypeScript type generation (`make types-generate`)
4. Frontend components use generated types

**To add new ranking sources:**
1. Update backend to scrape new source
2. Existing frontend will automatically support it (source is a query param)
3. Just change default from `"fightmatrix"` to new source name

**Performance considerations:**
- Rankings pages use `dynamic = 'force-dynamic'` for fresh data
- Consider adding ISR (Incremental Static Regeneration) with `revalidate` if rankings update predictably
- Chart component is client-side for interactivity
- Peak ranking could be moved to SSR if performance is critical

**Dependencies:**
- `recharts` - Already installed for other charts (TrendChart, etc.)
- `openapi-fetch` - Already used project-wide
- No new dependencies required

---

## Success Criteria

✅ All pages load without errors
✅ TypeScript compilation passes
✅ Linting passes
✅ Rankings data displays correctly from API
✅ Charts render and are interactive
✅ Navigation works across all pages
✅ Responsive design on mobile
✅ Error states handled gracefully
✅ Fighter detail page shows rankings when available

---

**Plan complete! Ready for execution with superpowers:executing-plans or superpowers:subagent-driven-development.**

Current date and time: 11/10/2025 03:14 PM
