"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import type { DivisionBreakdownEntry } from "./insight-utils";

type FightWebLegendProps = {
  palette: Map<string, string>;
  breakdown: DivisionBreakdownEntry[];
};

/**
 * Render a colour legend for the graph, combining server-provided colours and
 * division coverage counts.
 */
export function FightWebLegend({ palette, breakdown }: FightWebLegendProps) {
  if (palette.size === 0) {
    return null;
  }

  const paletteEntries = Array.from(palette.entries()).sort((a, b) => {
    const aCount =
      breakdown.find((entry) => entry.division === a[0])?.count ?? 0;
    const bCount =
      breakdown.find((entry) => entry.division === b[0])?.count ?? 0;
    return bCount - aCount;
  });
  const breakdownMap = new Map(
    breakdown.map((entry) => [entry.division, entry]),
  );

  return (
    <Card className="border border-border/80 bg-card/60">
      <CardHeader>
        <CardTitle className="text-sm font-semibold uppercase tracking-[0.3em] text-muted-foreground">
          Division legend
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-muted-foreground">
        {paletteEntries.map(([division, color]) => {
          const breakdownEntry = breakdownMap.get(division);
          const label = breakdownEntry
            ? `${breakdownEntry.count} fighters • ${breakdownEntry.percentage}%`
            : "No fighters in current slice";
          return (
            <div
              key={division}
              className="flex items-center justify-between rounded-2xl border border-border/70 bg-background/60 px-3 py-2"
            >
              <div className="flex items-center gap-3">
                <span
                  aria-hidden
                  className="inline-flex h-3.5 w-3.5 rounded-full"
                  style={{ backgroundColor: color }}
                />
                <span className="font-medium text-foreground/90">
                  {division}
                </span>
              </div>
              <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground/70">
                {label}
              </span>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
