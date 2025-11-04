"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { FightGraphQueryParams } from "@/lib/types";

import type { FightWebInsights } from "./insight-utils";

type FightWebSummaryProps = {
  nodeCount: number;
  linkCount: number;
  filters: FightGraphQueryParams;
  fallbackLimit: number;
  insights: FightWebInsights;
};

function formatNumber(value: number): string {
  return value.toLocaleString("en-US");
}

function formatDensity(density: number): string {
  return density.toFixed(3);
}

function formatLimit(
  filters: FightGraphQueryParams,
  fallbackLimit: number,
): number {
  return filters.limit ?? fallbackLimit;
}

function describeTimeRange(filters: FightGraphQueryParams): string {
  const start = filters.startYear ?? null;
  const end = filters.endYear ?? null;
  if (start && end) {
    return `${start} – ${end}`;
  }
  if (start) {
    return `${start} onward`;
  }
  if (end) {
    return `≤ ${end}`;
  }
  return "All recorded years";
}

/**
 * Display high-level metrics that summarise the currently applied FightWeb view.
 */
export function FightWebSummary({
  nodeCount,
  linkCount,
  filters,
  fallbackLimit,
  insights,
}: FightWebSummaryProps) {
  const divisionLabel =
    filters.division && filters.division.trim().length > 0
      ? filters.division
      : "All divisions";

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <Card>
        <CardHeader>
          <CardTitle>Indexed Fighters</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="text-3xl font-semibold tracking-tight">
            {formatNumber(nodeCount)}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Fighters represented in the current network slice.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Fight Connections</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="text-3xl font-semibold tracking-tight">
            {formatNumber(linkCount)}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Unique rivalries connecting the selected fighters.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Network Density</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="text-3xl font-semibold tracking-tight">
            {formatDensity(insights.networkDensity)}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Normalized connectivity score showing how tightly packed the graph
            is.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Scope</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 pt-0 text-sm text-muted-foreground">
          <div className="font-medium text-foreground">{divisionLabel}</div>
          <div>{describeTimeRange(filters)}</div>
          <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground/80">
            Limit {formatNumber(formatLimit(filters, fallbackLimit))}
            {" • "}
            {filters.includeUpcoming
              ? "Upcoming included"
              : "Upcoming excluded"}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
