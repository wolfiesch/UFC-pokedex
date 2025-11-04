"use client";

import { useEffect, useMemo, useState } from "react";

import type { FightGraphQueryParams } from "@/lib/types";

import {
  clampLimit,
  MAX_LIMIT,
  MIN_LIMIT,
  normalizeFilters,
} from "./filter-utils";

type FightWebFiltersProps = {
  filters: FightGraphQueryParams;
  onApply: (nextFilters: FightGraphQueryParams) => void | Promise<void>;
  onReset: () => void | Promise<void>;
  availableDivisions: string[];
  yearBounds: { min: number; max: number } | null;
  isLoading?: boolean;
};

export function FightWebFilters({
  filters,
  onApply,
  onReset,
  availableDivisions,
  yearBounds,
  isLoading = false,
}: FightWebFiltersProps) {
  const [draft, setDraft] = useState<FightGraphQueryParams>(
    normalizeFilters(filters)
  );

  useEffect(() => {
    setDraft(normalizeFilters(filters));
  }, [filters]);

  const sortedDivisions = useMemo(() => {
    return [...availableDivisions].sort((a, b) => a.localeCompare(b));
  }, [availableDivisions]);

  const currentBounds = useMemo(() => {
    if (!yearBounds) {
      return null;
    }
    return {
      min: yearBounds.min,
      max: yearBounds.max,
    };
  }, [yearBounds]);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onApply(normalizeFilters(draft));
  };

  const handleResetClick = () => {
    onReset();
  };

  return (
    <aside className="space-y-4 rounded-3xl border border-border/80 bg-card/60 p-6">
      <header className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">
          Filters
        </h2>
        <p className="text-sm text-muted-foreground">
          Refine the network by narrowing the weight class, year range, or node
          count. Apply changes to refresh the graph.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="space-y-4">
        <label className="flex flex-col gap-2 text-sm">
          <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
            Division
          </span>
          <select
            value={draft.division ?? "ALL"}
            onChange={(event) => {
              const value = event.target.value;
              setDraft((prev) => ({
                ...prev,
                division: value === "ALL" ? null : value,
              }));
            }}
            className="w-full rounded-2xl border border-border bg-background px-3 py-2 text-sm text-foreground shadow-sm outline-none transition focus:border-foreground focus:ring-2 focus:ring-foreground/20"
          >
            <option value="ALL">All divisions</option>
            {sortedDivisions.map((division) => (
              <option key={division} value={division}>
                {division}
              </option>
            ))}
          </select>
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-2 text-sm">
            <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
              Start year
            </span>
            <input
              type="number"
              inputMode="numeric"
              value={draft.startYear ?? ""}
              placeholder={currentBounds ? String(currentBounds.min) : "Any"}
              onChange={(event) => {
                const value = event.target.value;
                setDraft((prev) => ({
                  ...prev,
                  startYear: value === "" ? null : Number(value),
                }));
              }}
              className="w-full rounded-2xl border border-border bg-background px-3 py-2 text-sm text-foreground shadow-sm outline-none transition focus:border-foreground focus:ring-2 focus:ring-foreground/20"
            />
          </label>

          <label className="flex flex-col gap-2 text-sm">
            <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
              End year
            </span>
            <input
              type="number"
              inputMode="numeric"
              value={draft.endYear ?? ""}
              placeholder={currentBounds ? String(currentBounds.max) : "Any"}
              onChange={(event) => {
                const value = event.target.value;
                setDraft((prev) => ({
                  ...prev,
                  endYear: value === "" ? null : Number(value),
                }));
              }}
              className="w-full rounded-2xl border border-border bg-background px-3 py-2 text-sm text-foreground shadow-sm outline-none transition focus:border-foreground focus:ring-2 focus:ring-foreground/20"
            />
          </label>
        </div>

        <label className="flex flex-col gap-2 text-sm">
          <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
            Node limit
          </span>
          <input
            type="number"
            min={MIN_LIMIT}
            max={MAX_LIMIT}
            step={5}
            value={draft.limit ?? ""}
            onChange={(event) => {
              const value = Number(event.target.value);
              setDraft((prev) => ({
                ...prev,
                limit: Number.isNaN(value) ? prev.limit : clampLimit(value),
              }));
            }}
            className="w-full rounded-2xl border border-border bg-background px-3 py-2 text-sm text-foreground shadow-sm outline-none transition focus:border-foreground focus:ring-2 focus:ring-foreground/20"
          />
          <span className="text-xs text-muted-foreground">
            Between {MIN_LIMIT} and {MAX_LIMIT} fighters.
          </span>
        </label>

        <label className="flex items-center justify-between rounded-2xl border border-border bg-background/80 px-4 py-3 text-sm text-foreground shadow-sm">
          <div>
            <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
              Include upcoming bouts
            </div>
            <p className="text-xs text-muted-foreground">
              Toggle to include fights marked as “Next”.
            </p>
          </div>
          <input
            type="checkbox"
            checked={Boolean(draft.includeUpcoming)}
            onChange={(event) =>
              setDraft((prev) => ({
                ...prev,
                includeUpcoming: event.target.checked,
              }))
            }
            className="h-4 w-4 rounded border border-border text-foreground focus:ring-foreground/20"
          />
        </label>

        <div className="flex flex-col gap-2 pt-2 sm:flex-row sm:items-center sm:justify-between">
          <button
            type="submit"
            disabled={isLoading}
            className="inline-flex items-center justify-center rounded-full bg-foreground px-4 py-2 text-sm font-semibold text-background transition hover:bg-foreground/90 disabled:cursor-not-allowed disabled:bg-foreground/60"
          >
            {isLoading ? "Updating…" : "Apply filters"}
          </button>
          <button
            type="button"
            onClick={handleResetClick}
            disabled={isLoading}
            className="inline-flex items-center justify-center rounded-full border border-border px-4 py-2 text-sm text-muted-foreground transition hover:border-foreground hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60"
          >
            Reset to defaults
          </button>
        </div>
      </form>
    </aside>
  );
}
