"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Loader2 } from "lucide-react";

import type { FightGraphQueryParams } from "@/lib/types";

import {
  clampLimit,
  filtersEqual,
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
  isRefreshing?: boolean;
  error?: string | null;
  onRetry?: () => void | Promise<void>;
};

export function FightWebFilters({
  filters,
  onApply,
  onReset,
  availableDivisions,
  yearBounds,
  isLoading = false,
  isRefreshing = false,
  error = null,
  onRetry,
}: FightWebFiltersProps) {
  const [draft, setDraft] = useState<FightGraphQueryParams>(
    normalizeFilters(filters)
  );
  const isInitialMount = useRef(true);

  useEffect(() => {
    setDraft(normalizeFilters(filters));
    isInitialMount.current = true;
  }, [filters]);

  // Auto-apply filters with debouncing
  useEffect(() => {
    // Skip auto-apply on initial mount
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }

    // Skip if draft hasn't changed from current filters
    const normalizedDraft = normalizeFilters(draft);
    if (filtersEqual(normalizedDraft, filters)) {
      return;
    }

    // Debounce the apply call
    const timeoutId = setTimeout(() => {
      void onApply(normalizedDraft);
    }, 400);

    return () => {
      clearTimeout(timeoutId);
    };
  }, [draft, filters, onApply]);

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
      <div className="space-y-3">
        {isRefreshing && (
          <div
            className="flex items-center gap-2 rounded-2xl border border-dashed border-border/80 bg-muted/30 px-3 py-2 text-xs font-medium text-muted-foreground"
            role="status"
            aria-live="polite"
            aria-label="Refreshing fight graph"
          >
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span>Refreshing graph data…</span>
          </div>
        )}

        {error && (
          <div className="space-y-2 rounded-2xl border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">
            <p className="font-medium">{error}</p>
            {onRetry && (
              <button
                type="button"
                onClick={() => {
                  onRetry();
                }}
                className="inline-flex items-center justify-center rounded-full border border-destructive/50 px-3 py-1 text-xs font-semibold text-destructive transition hover:border-destructive hover:bg-destructive/10"
              >
                Retry request
              </button>
            )}
          </div>
        )}
      </div>

      <header className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">
          Filters
        </h2>
        <p className="text-sm text-muted-foreground">
          Refine the network by narrowing the weight class, year range, or node
          count. Filters apply automatically as you adjust them.
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

        <div className="flex flex-col gap-2 pt-2 sm:flex-row sm:items-center sm:justify-end">
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
