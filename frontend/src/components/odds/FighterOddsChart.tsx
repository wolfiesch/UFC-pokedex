"use client";

import { useMemo } from "react";
import { format } from "date-fns";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { FighterOddsChartFight } from "@/types/odds";
import { QualityBadge } from "./QualityBadge";

type FighterOddsChartProps = {
  fights: FighterOddsChartFight[];
  selectedFightId?: string;
};

type ChartPoint = {
  timestamp_ms: number;
  label: string;
  odds: number;
};

export function FighterOddsChart({
  fights,
  selectedFightId,
}: FighterOddsChartProps) {
  const selectedFight =
    fights.find((fight) => fight.fight_id === selectedFightId) ?? fights[0];

  const chartData: ChartPoint[] = useMemo(() => {
    if (!selectedFight?.time_series?.length) {
      return [];
    }
    return selectedFight.time_series
      .filter((point) => typeof point.odds === "number")
      .map((point) => {
        const date = new Date(point.timestamp ?? point.timestamp_ms);
        return {
          timestamp_ms: point.timestamp_ms,
          odds: point.odds,
          label: format(date, "MMM d"),
        };
      });
  }, [selectedFight]);

  if (!selectedFight) {
    return (
      <Card className="bg-card/60">
        <CardHeader>
          <CardTitle className="text-base text-muted-foreground">
            Betting Odds
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No odds data available yet. Check back after the next scrape cycle.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/60">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-3">
              <CardTitle className="text-xl">Betting Odds Timeline</CardTitle>
              <span className="rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-primary">
                Selected fight
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              vs. {selectedFight.opponent} ·{" "}
              {selectedFight.event} ·{" "}
              {selectedFight.event_date
                ? format(new Date(selectedFight.event_date), "MMM d, yyyy")
                : "Date TBA"}
            </p>
          </div>
          <div className="text-right text-xs text-muted-foreground">
            <p>
              Opening:{" "}
              <span className="font-semibold text-foreground">
                {selectedFight.opening_odds ?? "—"}
              </span>
            </p>
            <p>
              Closing:{" "}
              <span className="font-semibold text-foreground">
                {selectedFight.closing_odds ?? "—"}
              </span>
            </p>
            <div className="mt-2 flex justify-end">
              <QualityBadge tier={selectedFight.quality} />
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="h-80">
        {chartData.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} className="-mx-4">
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
              <XAxis
                dataKey="label"
                stroke="currentColor"
                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
              />
              <YAxis
                stroke="currentColor"
                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                tickFormatter={(value) => value.toFixed(2)}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  const point = payload[0].payload as ChartPoint;
                  return (
                    <div className="rounded-lg border bg-background/95 p-3 shadow-lg">
                      <p className="text-xs text-muted-foreground">
                        {format(new Date(point.timestamp_ms), "PPpp")}
                      </p>
                      <p className="text-sm font-semibold text-foreground">
                        {point.odds.toFixed(2)} (decimal)
                      </p>
                    </div>
                  );
                }}
              />
              <Line
                type="monotone"
                dataKey="odds"
                stroke="hsl(var(--primary))"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center rounded-2xl bg-muted/40 text-sm text-muted-foreground">
            No time-series points available for this fight.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
