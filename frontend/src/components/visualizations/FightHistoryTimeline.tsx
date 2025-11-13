"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ZAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { FightHistoryEntry } from "@/lib/types";

interface FightHistoryTimelineProps {
  fightHistory: FightHistoryEntry[];
  fighterName: string;
}

type FilterType = "all" | "wins" | "losses" | "draws";
type MethodFilter = "all" | "ko" | "submission" | "decision";

function getResultColor(result: string): string {
  const resultLower = result.toLowerCase();
  if (resultLower.includes("win")) {
    return "hsl(120, 30%, 45%)"; // Greenish
  } else if (resultLower.includes("draw")) {
    return "hsl(0, 0%, 50%)"; // Gray
  } else {
    return "hsl(0, 30%, 45%)"; // Reddish
  }
}

function getResultCategory(result: string): FilterType {
  const resultLower = result.toLowerCase();
  if (resultLower.includes("win")) return "wins";
  if (resultLower.includes("draw")) return "draws";
  return "losses";
}

function getMethodCategory(method: string): MethodFilter {
  const methodUpper = method.toUpperCase();
  if (methodUpper.includes("KO") || methodUpper.includes("TKO")) return "ko";
  if (methodUpper.includes("SUB")) return "submission";
  if (methodUpper.includes("DEC")) return "decision";
  return "all";
}

// Calculate fight size based on round finished (quicker finish = larger dot)
function getFightSize(round?: number | null, totalRounds: number = 3): number {
  if (!round) return 8; // Default size
  // Inverted: round 1 finish = larger, round 3 = smaller
  const sizeRange = 15 - 6; // Range from 6 to 15
  const normalizedRound = (totalRounds - round + 1) / totalRounds;
  return 6 + normalizedRound * sizeRange;
}

// Get the earliest fight year from fight history
function getFirstFightYear(fights: FightHistoryEntry[]): number {
  const validFights = fights.filter((f) => f.event_date);
  if (validFights.length === 0) return new Date().getFullYear();
  const dates = validFights.map((f) => new Date(f.event_date!).getFullYear());
  return Math.min(...dates);
}

// Generate monthly tick marks from start year to end year
function generateMonthlyTicks(startYear: number, endYear: number): number[] {
  const ticks: number[] = [];
  for (let year = startYear; year <= endYear; year++) {
    for (let month = 0; month < 12; month++) {
      ticks.push(new Date(year, month, 1).getTime());
    }
  }
  return ticks;
}

// Custom tick component for timeline axis
interface TimelineAxisTickProps {
  x: number;
  y: number;
  payload: { value: number };
}

const TimelineAxisTick = ({ x, y, payload }: TimelineAxisTickProps) => {
  const date = new Date(payload.value);
  const month = date.getMonth();
  const isYearStart = month === 0; // January = year boundary
  const isQuarterly = month === 2 || month === 5 || month === 8; // March, June, September

  // Determine tick line properties based on type
  const tickHeight = isYearStart ? 12 : isQuarterly ? 8 : 5;
  const tickStrokeWidth = isYearStart ? 2.5 : isQuarterly ? 1.8 : 1;
  const tickOpacity = isYearStart ? 1 : isQuarterly ? 0.8 : 0.4;

  return (
    <g transform={`translate(${x},${y})`}>
      {/* Tick line with hierarchy: annual > quarterly > monthly */}
      <line
        x1={0}
        y1={0}
        x2={0}
        y2={tickHeight}
        stroke="hsl(var(--border))"
        strokeWidth={tickStrokeWidth}
        opacity={tickOpacity}
      />
      {/* Label (only show for years) */}
      {isYearStart && (
        <text
          x={0}
          y={22}
          textAnchor="middle"
          fill="hsl(var(--muted-foreground))"
          fontSize={11}
          fontWeight={500}
        >
          {date.getFullYear()}
        </text>
      )}
    </g>
  );
};

export function FightHistoryTimeline({
  fightHistory,
  fighterName,
}: FightHistoryTimelineProps) {
  const [resultFilter, setResultFilter] = useState<FilterType>("all");
  const [methodFilter, setMethodFilter] = useState<MethodFilter>("all");

  // Sort fights by date (most recent first for display)
  const sortedFights = [...fightHistory]
    .filter((f) => f.event_date)
    .sort(
      (a, b) =>
        new Date(b.event_date!).getTime() - new Date(a.event_date!).getTime(),
    );

  if (sortedFights.length === 0) {
    return (
      <Card className="bg-card/80">
        <CardHeader>
          <CardTitle className="text-xl">Fight Timeline</CardTitle>
        </CardHeader>
        <CardContent className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">
          No fight history with dates available.
        </CardContent>
      </Card>
    );
  }

  // Filter fights
  const filteredFights = sortedFights.filter((fight) => {
    const resultMatch =
      resultFilter === "all" ||
      getResultCategory(fight.result) === resultFilter;
    const methodMatch =
      methodFilter === "all" ||
      getMethodCategory(fight.method) === methodFilter;
    return resultMatch && methodMatch;
  });

  // Prepare data for scatter chart
  // X-axis: date, Y-axis: fight index (for vertical spacing), Z-axis: size
  const chartData = filteredFights.map((fight, index) => ({
    date: new Date(fight.event_date!).getTime(),
    index: index,
    size: getFightSize(fight.round),
    result: fight.result,
    method: fight.method,
    opponent: fight.opponent,
    opponent_id: fight.opponent_id,
    event_name: fight.event_name,
    round: fight.round,
    time: fight.time,
    color: getResultColor(fight.result),
  }));

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload[0]) return null;

    const data = payload[0].payload;
    return (
      <div className="rounded-xl border border-border/80 bg-background/95 p-3 text-xs shadow-lg">
        <div className="mb-2 font-semibold text-foreground">
          {data.event_name}
        </div>
        <div className="mb-1 text-muted-foreground">vs {data.opponent}</div>
        <div className="flex items-center gap-2">
          <Badge
            variant={
              data.result.toLowerCase().includes("win") ? "default" : "outline"
            }
            className="text-xs"
          >
            {data.result}
          </Badge>
          <span className="text-muted-foreground">
            {data.method}
            {data.round &&
              ` (R${data.round}${data.time ? `, ${data.time}` : ""})`}
          </span>
        </div>
        <div className="mt-1 text-xs text-muted-foreground/70">
          {new Date(data.date).toLocaleDateString()}
        </div>
      </div>
    );
  };

  const stats = {
    total: sortedFights.length,
    wins: sortedFights.filter((f) => f.result.toLowerCase().includes("win"))
      .length,
    losses: sortedFights.filter((f) => f.result.toLowerCase().includes("loss"))
      .length,
    draws: sortedFights.filter((f) => f.result.toLowerCase().includes("draw"))
      .length,
  };

  // Calculate custom domain bounds and tick marks
  const firstFightYear = getFirstFightYear(sortedFights);
  const currentYear = 2025;
  const domainStart = new Date(firstFightYear, 0, 1).getTime(); // Jan 1 of first fight year
  const domainEnd = new Date(currentYear, 11, 31).getTime(); // Dec 31, 2025
  const monthlyTicks = generateMonthlyTicks(firstFightYear, currentYear);

  return (
    <Card className="bg-card/80">
      <CardHeader>
        <CardTitle className="text-xl">Fight Timeline</CardTitle>
        <p className="text-sm text-muted-foreground">
          Chronological fight history with results. Larger dots = quicker
          finishes.
        </p>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 pt-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
              Result
            </label>
            <div className="flex gap-1">
              <button
                onClick={() => setResultFilter("all")}
                className={`rounded-lg border px-3 py-1 text-xs transition ${
                  resultFilter === "all"
                    ? "border-foreground bg-foreground text-background"
                    : "border-border bg-background text-foreground hover:border-foreground"
                }`}
              >
                All ({stats.total})
              </button>
              <button
                onClick={() => setResultFilter("wins")}
                className={`rounded-lg border px-3 py-1 text-xs transition ${
                  resultFilter === "wins"
                    ? "border-foreground bg-foreground text-background"
                    : "border-border bg-background text-foreground hover:border-foreground"
                }`}
              >
                Wins ({stats.wins})
              </button>
              <button
                onClick={() => setResultFilter("losses")}
                className={`rounded-lg border px-3 py-1 text-xs transition ${
                  resultFilter === "losses"
                    ? "border-foreground bg-foreground text-background"
                    : "border-border bg-background text-foreground hover:border-foreground"
                }`}
              >
                Losses ({stats.losses})
              </button>
              {stats.draws > 0 && (
                <button
                  onClick={() => setResultFilter("draws")}
                  className={`rounded-lg border px-3 py-1 text-xs transition ${
                    resultFilter === "draws"
                      ? "border-foreground bg-foreground text-background"
                      : "border-border bg-background text-foreground hover:border-foreground"
                  }`}
                >
                  Draws ({stats.draws})
                </button>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
              Method
            </label>
            <div className="flex gap-1">
              <button
                onClick={() => setMethodFilter("all")}
                className={`rounded-lg border px-3 py-1 text-xs transition ${
                  methodFilter === "all"
                    ? "border-foreground bg-foreground text-background"
                    : "border-border bg-background text-foreground hover:border-foreground"
                }`}
              >
                All
              </button>
              <button
                onClick={() => setMethodFilter("ko")}
                className={`rounded-lg border px-3 py-1 text-xs transition ${
                  methodFilter === "ko"
                    ? "border-foreground bg-foreground text-background"
                    : "border-border bg-background text-foreground hover:border-foreground"
                }`}
              >
                KO/TKO
              </button>
              <button
                onClick={() => setMethodFilter("submission")}
                className={`rounded-lg border px-3 py-1 text-xs transition ${
                  methodFilter === "submission"
                    ? "border-foreground bg-foreground text-background"
                    : "border-border bg-background text-foreground hover:border-foreground"
                }`}
              >
                Sub
              </button>
              <button
                onClick={() => setMethodFilter("decision")}
                className={`rounded-lg border px-3 py-1 text-xs transition ${
                  methodFilter === "decision"
                    ? "border-foreground bg-foreground text-background"
                    : "border-border bg-background text-foreground hover:border-foreground"
                }`}
              >
                Decision
              </button>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {filteredFights.length === 0 ? (
          <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">
            No fights match the current filters.
          </div>
        ) : (
          <ResponsiveContainer
            width="100%"
            height={Math.max(300, filteredFights.length * 40)}
          >
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 10 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
                strokeOpacity={0.2}
              />
              <XAxis
                type="number"
                dataKey="date"
                domain={[domainStart, domainEnd]}
                ticks={monthlyTicks}
                tick={TimelineAxisTick as any}
                interval={0}
                height={40}
                stroke="hsl(var(--border))"
              />
              <YAxis
                type="number"
                dataKey="index"
                hide={true}
                domain={[0, filteredFights.length - 1]}
              />
              <ZAxis type="number" dataKey="size" range={[50, 400]} />
              <Tooltip
                content={<CustomTooltip />}
                cursor={{ strokeDasharray: "3 3" }}
              />
              <Scatter data={chartData} fill="hsl(var(--foreground))">
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        )}

        {/* Legend */}
        <div className="mt-6 flex flex-wrap justify-center gap-4 border-t border-border pt-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-full"
              style={{ backgroundColor: "hsl(120, 30%, 45%)" }}
            />
            <span>Win</span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-full"
              style={{ backgroundColor: "hsl(0, 30%, 45%)" }}
            />
            <span>Loss</span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-full"
              style={{ backgroundColor: "hsl(0, 0%, 50%)" }}
            />
            <span>Draw</span>
          </div>
          <div className="ml-4 flex items-center gap-2">
            <span>Dot size = Finish speed</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
