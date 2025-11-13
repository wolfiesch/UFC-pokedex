"use client";

import type { ChangeEvent } from "react";

import { Button } from "@/components/ui/button";
import ChampionStatusFilter from "@/components/filters/ChampionStatusFilter";
import { StreakFilter } from "@/components/filters/StreakFilter";

type FilterPanelProps = {
  stances: string[];
  selectedStance: string | null;
  onStanceChange: (stance: string | null) => void;
  divisions: string[];
  selectedDivision: string | null;
  onDivisionChange: (division: string | null) => void;
  nationalities?: Array<{ code: string; label: string }>;
  selectedNationality: string | null;
  onNationalityChange: (nationality: string | null) => void;
  championStatusFilters: string[];
  onToggleChampionStatus: (status: string) => void;
  winStreakCount: number | null;
  lossStreakCount: number | null;
  onWinStreakChange: (count: number | null) => void;
  onLossStreakChange: (count: number | null) => void;
};

export default function FilterPanel({
  stances,
  selectedStance,
  onStanceChange,
  divisions,
  selectedDivision,
  onDivisionChange,
  nationalities = [],
  selectedNationality,
  onNationalityChange,
  championStatusFilters,
  onToggleChampionStatus,
  winStreakCount,
  lossStreakCount,
  onWinStreakChange,
  onLossStreakChange,
}: FilterPanelProps) {
  const handleStanceChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    onStanceChange(value === "all" ? null : value);
  };

  const handleDivisionChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    onDivisionChange(value === "all" ? null : value);
  };

  const handleNationalityChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    onNationalityChange(value === "all" ? null : value);
  };

  const hasActiveFilters =
    selectedStance ||
    selectedDivision ||
    selectedNationality ||
    championStatusFilters.length > 0 ||
    winStreakCount !== null ||
    lossStreakCount !== null;

  const handleClearFilters = () => {
    onStanceChange(null);
    onDivisionChange(null);
    onNationalityChange(null);
    // Clear all champion status filters
    championStatusFilters.forEach((status) => onToggleChampionStatus(status));
    // Clear streak filters
    onWinStreakChange(null);
    onLossStreakChange(null);
  };

  return (
    <div className="flex flex-col gap-3 rounded-3xl border border-border bg-card/60 p-4 shadow-subtle sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-col gap-3 sm:flex-row sm:gap-4">
        <div className="flex flex-col gap-1">
          <label
            htmlFor="stance-filter"
            className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground"
          >
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
          <label
            htmlFor="division-filter"
            className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground"
          >
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
        {nationalities.length > 0 && (
          <div className="flex flex-col gap-1">
            <label
              htmlFor="nationality-filter"
              className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground"
            >
              Nationality
            </label>
            <select
              id="nationality-filter"
              value={selectedNationality ?? "all"}
              onChange={handleNationalityChange}
              className="h-10 w-full rounded-xl border border-input bg-background px-4 text-sm text-foreground transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:w-48"
            >
              <option value="all">All Nationalities</option>
              {nationalities.map(({ code, label }) => (
                <option key={code} value={code}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        )}
        <ChampionStatusFilter
          selectedStatuses={championStatusFilters}
          onToggleStatus={onToggleChampionStatus}
        />
        <StreakFilter
          winStreakCount={winStreakCount}
          lossStreakCount={lossStreakCount}
          onWinStreakChange={onWinStreakChange}
          onLossStreakChange={onLossStreakChange}
        />
      </div>
      {hasActiveFilters ? (
        <Button
          variant="ghost"
          className="w-full justify-center sm:w-auto"
          onClick={handleClearFilters}
        >
          Clear filters
        </Button>
      ) : null}
    </div>
  );
}
