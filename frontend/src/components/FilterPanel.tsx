"use client";

import { useEffect, useState, type ChangeEvent } from "react";
import { ChevronDown } from "lucide-react";

import SearchBar from "@/components/SearchBar";
import { Button } from "@/components/ui/button";
import ChampionStatusFilter from "@/components/filters/ChampionStatusFilter";
import { StreakFilter } from "@/components/filters/StreakFilter";
import { cn } from "@/lib/utils";

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
  isSearching?: boolean;
  onResetFilters?: () => void;
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
  isSearching = false,
  onResetFilters,
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

  const hasAnyFilters =
    selectedStance ||
    selectedDivision ||
    selectedNationality ||
    championStatusFilters.length > 0 ||
    winStreakCount !== null ||
    lossStreakCount !== null;

  const hasAdvancedFilters =
    selectedNationality ||
    championStatusFilters.length > 0 ||
    winStreakCount !== null ||
    lossStreakCount !== null;

  const advancedActiveCount =
    (selectedNationality ? 1 : 0) +
    championStatusFilters.length +
    (winStreakCount !== null ? 1 : 0) +
    (lossStreakCount !== null ? 1 : 0);

  const [isAdvancedOpen, setIsAdvancedOpen] = useState(hasAdvancedFilters);

  useEffect(() => {
    if (hasAdvancedFilters) {
      setIsAdvancedOpen(true);
    }
  }, [hasAdvancedFilters]);

  return (
    <section
      className="space-y-6 rounded-3xl border border-border bg-card/70 p-6 shadow-subtle"
      aria-label="Roster controls"
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">
              Primary filters
            </p>
            <p className="text-sm text-muted-foreground/80">
              Search by name and narrow by stance or division.
            </p>
          </div>
          {hasAnyFilters && onResetFilters ? (
            <Button
              variant="ghost"
              size="sm"
              className="rounded-full"
              onClick={onResetFilters}
            >
              Reset filters
            </Button>
          ) : null}
        </div>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-stretch">
          <SearchBar isLoading={isSearching} className="flex-1" />
          <div className="grid flex-1 gap-4 sm:grid-cols-2">
            <FilterSelect
              id="stance-filter"
              label="Stance"
              value={selectedStance ?? "all"}
              onChange={handleStanceChange}
              options={[
                { value: "all", label: "All stances" },
                ...stances.map((stance) => ({ value: stance, label: stance })),
              ]}
            />
            <FilterSelect
              id="division-filter"
              label="Division"
              value={selectedDivision ?? "all"}
              onChange={handleDivisionChange}
              options={[
                { value: "all", label: "All divisions" },
                ...divisions.map((division) => ({
                  value: division,
                  label: division,
                })),
              ]}
            />
          </div>
        </div>
      </div>

      {nationalities.length > 0 ? (
        <div>
          <button
            type="button"
            onClick={() => setIsAdvancedOpen((prev) => !prev)}
            className="flex w-full items-center justify-between rounded-2xl border border-border/80 bg-background/60 px-4 py-3 text-left transition hover:border-border"
            aria-expanded={isAdvancedOpen}
          >
            <div>
              <p className="text-sm font-semibold text-foreground">
                Advanced filters
              </p>
              <p className="text-xs text-muted-foreground">
                Nationality, champion flags, and streak sliders.
              </p>
            </div>
            <div className="flex items-center gap-3">
              {advancedActiveCount > 0 ? (
                <span className="rounded-full bg-accent px-3 py-1 text-xs font-semibold text-accent-foreground">
                  {advancedActiveCount} active
                </span>
              ) : null}
              <ChevronDown
                className={cn(
                  "h-5 w-5 text-muted-foreground transition-transform",
                  isAdvancedOpen ? "rotate-180" : "",
                )}
                aria-hidden
              />
            </div>
          </button>
          <div
            className={cn(
              "space-y-6 pt-6",
              isAdvancedOpen ? "block" : "hidden",
            )}
            aria-hidden={!isAdvancedOpen}
          >
            <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
              <FilterSelect
                id="nationality-filter"
                label="Nationality"
                value={selectedNationality ?? "all"}
                onChange={handleNationalityChange}
                options={[
                  { value: "all", label: "All nationalities" },
                  ...nationalities.map(({ code, label }) => ({
                    value: code,
                    label,
                  })),
                ]}
              />
              <ChampionStatusFilter
                selectedStatuses={championStatusFilters}
                onToggleStatus={onToggleChampionStatus}
              />
            </div>
            <div className="rounded-2xl border border-border/80 bg-background/60 p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">
                Streak filters
              </p>
              <StreakFilter
                winStreakCount={winStreakCount}
                lossStreakCount={lossStreakCount}
                onWinStreakChange={onWinStreakChange}
                onLossStreakChange={onLossStreakChange}
              />
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

type FilterSelectProps = {
  id: string;
  label: string;
  value: string;
  onChange: (event: ChangeEvent<HTMLSelectElement>) => void;
  options: Array<{ value: string; label: string }>;
};

function FilterSelect({
  id,
  label,
  value,
  onChange,
  options,
}: FilterSelectProps) {
  return (
    <div className="flex flex-col gap-2">
      <label
        htmlFor={id}
        className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground"
      >
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={onChange}
        className="h-12 rounded-2xl border border-input bg-background px-4 text-sm text-foreground transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
