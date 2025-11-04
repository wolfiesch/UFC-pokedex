"use client";

import type { ChangeEvent } from "react";

import { Button } from "@/components/ui/button";
import ChampionStatusFilter from "@/components/filters/ChampionStatusFilter";

type FilterPanelProps = {
  stances: string[];
  selectedStance: string | null;
  onStanceChange: (stance: string | null) => void;
  divisions: string[];
  selectedDivision: string | null;
  onDivisionChange: (division: string | null) => void;
  championStatusFilters: string[];
  onToggleChampionStatus: (status: string) => void;
};

export default function FilterPanel({
  stances,
  selectedStance,
  onStanceChange,
  divisions,
  selectedDivision,
  onDivisionChange,
  championStatusFilters,
  onToggleChampionStatus,
}: FilterPanelProps) {
  const handleStanceChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    onStanceChange(value === "all" ? null : value);
  };

  const handleDivisionChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    onDivisionChange(value === "all" ? null : value);
  };

  return (
    <div className="flex flex-col gap-3 rounded-3xl border border-border bg-card/60 p-4 shadow-subtle sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-col gap-3 sm:flex-row sm:gap-4">
        <div className="flex flex-col gap-1">
          <label htmlFor="stance-filter" className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">
            Stance
          </label>
          <select
            id="stance-filter"
            value={selectedStance ?? "all"}
            onChange={handleStanceChange}
            className="h-10 w-full rounded-xl border border-input bg-background px-4 text-sm text-foreground transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:w-48"
          >
            <option value="all">All</option>
            {stances.map((stance) => (
              <option key={stance} value={stance}>
                {stance}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="division-filter" className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">
            Division
          </label>
          <select
            id="division-filter"
            value={selectedDivision ?? "all"}
            onChange={handleDivisionChange}
            className="h-10 w-full rounded-xl border border-input bg-background px-4 text-sm text-foreground transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:w-48"
          >
            <option value="all">All</option>
            {divisions.map((division) => (
              <option key={division} value={division}>
                {division}
              </option>
            ))}
          </select>
        </div>
      </div>
      {(selectedStance || selectedDivision) ? (
        <Button
          variant="ghost"
          className="w-full justify-center sm:w-auto"
          onClick={() => {
            onStanceChange(null);
            onDivisionChange(null);
          }}
        >
          Clear filters
        </Button>
      ) : null}
    </div>
  );
}
