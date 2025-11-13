"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  resolveDivisionColor,
  type DivisionColorRamp,
} from "@/constants/divisionColors";

import type { DivisionBreakdownEntry } from "./insight-utils";

type FightWebLegendProps = {
  palette: Map<string, DivisionColorRamp>;
  breakdown: DivisionBreakdownEntry[];
  isolatedDivision: string | null;
  onIsolate: (division: string | null) => void;
};

/**
 * Render a colour legend for the graph, combining server-provided colours and
 * division coverage counts.
 */
export function FightWebLegend({
  palette,
  breakdown,
  isolatedDivision,
  onIsolate,
}: FightWebLegendProps) {
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
  const normalizedIsolation = isolatedDivision?.trim() ?? null;

  return (
    <Card className="border border-border/80 bg-card/60">
      <CardHeader>
        <CardTitle className="text-sm font-semibold uppercase tracking-[0.3em] text-muted-foreground">
          Division legend
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm text-muted-foreground">
        <p className="text-xs text-muted-foreground/80">
          Toggle a division to isolate it in the network. Tap again to return to
          the full cross-division view.
        </p>
        <div className="grid gap-3 md:grid-cols-2">
          {paletteEntries.map(([division, ramp]) => {
            const normalizedDivision = division.trim();
            const breakdownEntry = breakdownMap.get(division);
            const label = breakdownEntry
              ? `${breakdownEntry.count} fighters • ${breakdownEntry.percentage}%`
              : "No fighters in current slice";
            const isActive = normalizedIsolation === normalizedDivision;
            const swatchGradient = `linear-gradient(135deg, ${ramp.muted} 0%, ${ramp.emphasis} 100%)`;
            return (
              <div
                key={division}
                className="flex items-center justify-between gap-4 rounded-2xl border border-border/70 bg-background/60 px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <span
                    aria-hidden
                    className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl shadow-inner"
                    style={{ backgroundImage: swatchGradient }}
                  >
                    <span
                      className="h-3 w-3 rounded-full"
                      style={{ backgroundColor: resolveDivisionColor(normalizedDivision) }}
                    />
                  </span>
                  <div className="space-y-1">
                    <p className="font-semibold text-foreground/90">{normalizedDivision}</p>
                    <p className="text-xs text-muted-foreground/80">{label}</p>
                  </div>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={Boolean(isActive)}
                  aria-label={`Isolate ${normalizedDivision}`}
                  onClick={() => onIsolate(isActive ? null : normalizedDivision)}
                  className={`relative inline-flex h-7 w-12 shrink-0 items-center rounded-full border transition ${
                    isActive
                      ? "border-foreground/60 bg-foreground/70"
                      : "border-border/70 bg-muted/40"
                  }`}
                >
                  <span
                    className={`absolute left-1 top-1 inline-block h-5 w-5 rounded-full bg-background shadow transition-transform ${
                      isActive ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
