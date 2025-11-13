"use client";

import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";

export interface LeaderboardFiltersProps {
  division: string | null;
  minFights: number;
  onDivisionChange: (division: string | null) => void;
  onMinFightsChange: (minFights: number) => void;
}

const DIVISIONS = [
  "Flyweight",
  "Bantamweight",
  "Featherweight",
  "Lightweight",
  "Welterweight",
  "Middleweight",
  "Light Heavyweight",
  "Heavyweight",
  "Strawweight",
  "Super Heavyweight",
] as const;

/**
 * Filter controls for leaderboards - allows users to narrow results by division
 * and minimum fight count for data quality.
 */
export default function LeaderboardFilters({
  division,
  minFights,
  onDivisionChange,
  onMinFightsChange,
}: LeaderboardFiltersProps) {
  return (
    <div className="rounded-3xl border border-border bg-card/80 p-6">
      <div className="mb-4">
        <h3 className="text-sm font-semibold uppercase tracking-[0.3em] text-muted-foreground">
          Filters
        </h3>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Division Filter */}
        <div className="space-y-3">
          <Label htmlFor="division-filter" className="text-sm font-medium">
            Weight Division
          </Label>
          <select
            id="division-filter"
            value={division ?? "all"}
            onChange={(event) => {
              const nextValue = event.target.value;
              onDivisionChange(nextValue === "all" ? null : nextValue);
            }}
            className="w-full rounded-xl border border-border bg-background/80 px-3 py-2 text-sm font-medium text-foreground shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          >
            <option value="all">All Divisions</option>
            {DIVISIONS.map((div) => (
              <option key={div} value={div}>
                {div}
              </option>
            ))}
          </select>
        </div>

        {/* Minimum Fights Filter */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label htmlFor="min-fights-filter" className="text-sm font-medium">
              Minimum UFC Fights
            </Label>
            <span className="rounded-full bg-muted px-3 py-1 font-mono text-xs font-semibold">
              {minFights}
            </span>
          </div>
          <Slider
            id="min-fights-filter"
            min={0}
            max={20}
            step={1}
            value={[minFights]}
            onValueChange={([value]) => onMinFightsChange(value)}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>0 fights</span>
            <span>20+ fights</span>
          </div>
        </div>
      </div>

      {/* Active Filters Summary */}
      {(division || minFights > 0) && (
        <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-4">
          <span className="text-xs uppercase tracking-wider text-muted-foreground">
            Active:
          </span>
          {division && (
            <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
              {division}
            </span>
          )}
          {minFights > 0 && (
            <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
              {minFights}+ fights
            </span>
          )}
          <button
            onClick={() => {
              onDivisionChange(null);
              onMinFightsChange(0);
            }}
            className="ml-auto text-xs text-muted-foreground underline underline-offset-2 transition-colors hover:text-foreground"
          >
            Clear all
          </button>
        </div>
      )}
    </div>
  );
}
