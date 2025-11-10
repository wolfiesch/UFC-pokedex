"use client";

import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
          <Select
            value={division || "all"}
            onValueChange={(value) => onDivisionChange(value === "all" ? null : value)}
          >
            <SelectTrigger id="division-filter" className="w-full">
              <SelectValue placeholder="All Divisions" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Divisions</SelectItem>
              {DIVISIONS.map((div) => (
                <SelectItem key={div} value={div}>
                  {div}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Minimum Fights Filter */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label htmlFor="min-fights-filter" className="text-sm font-medium">
              Minimum UFC Fights
            </Label>
            <span className="rounded-full bg-muted px-3 py-1 text-xs font-mono font-semibold">
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
            className="ml-auto text-xs text-muted-foreground hover:text-foreground underline underline-offset-2 transition-colors"
          >
            Clear all
          </button>
        </div>
      )}
    </div>
  );
}
