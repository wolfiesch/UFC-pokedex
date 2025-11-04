"use client";

import { useEffect, useMemo, useState } from "react";

import { compareFighters, searchFighters } from "@/lib/api";
import { formatCategoryLabel, formatMetricLabel } from "@/lib/format";
import type { FighterComparisonEntry, FighterListItem } from "@/lib/types";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const CATEGORY_KEYS = [
  "significant_strikes",
  "striking",
  "grappling",
  "takedown_stats",
  "career",
] as const;

type CategoryKey = (typeof CATEGORY_KEYS)[number];

type Props = {
  primaryFighterId: string;
  primaryFighterName: string;
};

type ComparisonState = {
  entries: FighterComparisonEntry[];
};

function categoryStats(entry: FighterComparisonEntry, category: CategoryKey) {
  return entry[category];
}

function normaliseValue(value: string | number | null | undefined): string {
  if (value === null || typeof value === "undefined") {
    return "—";
  }
  return typeof value === "number" ? value.toString() : value;
}

export default function FighterComparisonPanel({
  primaryFighterId,
  primaryFighterName,
}: Props) {
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<FighterListItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [comparison, setComparison] = useState<ComparisonState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setOptions([]);
      return;
    }

    let cancelled = false;
    setIsSearching(true);
    const timer = window.setTimeout(async () => {
      try {
        const results = await searchFighters(trimmed, null, null, 10, 0);
        if (!cancelled) {
          setOptions(
            results.fighters
              .filter((item: FighterListItem) => item.fighter_id !== primaryFighterId)
              .slice(0, 6)
          );
        }
      } catch (searchError) {
        if (!cancelled) {
          console.error("Failed to search fighters", searchError);
        }
      } finally {
        if (!cancelled) {
          setIsSearching(false);
        }
      }
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [primaryFighterId, query]);

  const fighterColumns = useMemo(() => comparison?.entries ?? [], [comparison]);

  const visibleCategories = useMemo(() => {
    if (!comparison) {
      return [];
    }
    return CATEGORY_KEYS.filter((category) =>
      comparison.entries.some(
        (entry) => Object.keys(categoryStats(entry, category)).length > 0
      )
    );
  }, [comparison]);

  async function handleSelect(option: FighterListItem) {
    if (!option || option.fighter_id === primaryFighterId) {
      return;
    }
    setError(null);
    setIsLoading(true);
    try {
      const response = await compareFighters([primaryFighterId, option.fighter_id]);
      if (response.fighters.length === 0) {
        setError("Comparison data is unavailable for the selected fighters.");
        setComparison(null);
      } else {
        setComparison({ entries: response.fighters });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to compare fighters");
      setComparison(null);
    } finally {
      setIsLoading(false);
    }
  }

  function handleReset() {
    setComparison(null);
    setOptions([]);
    setQuery("");
    setError(null);
  }

  return (
    <Card className="rounded-3xl border-border bg-card/80">
      <CardHeader className="space-y-2">
        <CardTitle className="text-2xl">Compare Stats</CardTitle>
        <CardDescription>
          Select another fighter to stack their metrics against {primaryFighterName || "this fighter"}.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-end">
          <div className="flex flex-1 flex-col gap-2">
            <label
              htmlFor="comparison-search"
              className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground"
            >
              Search fighters
            </label>
            <Input
              id="comparison-search"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Start typing a fighter name..."
            />
            {isSearching ? (
              <p className="text-xs text-muted-foreground">Searching…</p>
            ) : options.length > 0 ? (
              <ul className="grid gap-2">
                {options.map((option) => (
                  <li key={option.fighter_id}>
                    <button
                      type="button"
                      onClick={() => handleSelect(option)}
                      className="flex w-full flex-col rounded-2xl border border-border/70 bg-background/80 px-4 py-3 text-left transition hover:-translate-y-0.5 hover:border-foreground/20 hover:bg-background"
                    >
                      <span className="text-sm font-semibold">{option.name}</span>
                      {option.nickname ? (
                        <span className="text-xs text-muted-foreground">
                          &ldquo;{option.nickname}&rdquo;
                        </span>
                      ) : null}
                    </button>
                  </li>
                ))}
              </ul>
            ) : query.trim().length >= 2 ? (
              <p className="text-xs text-muted-foreground">No fighters matched that search.</p>
            ) : null}
          </div>
          <Button
            variant="ghost"
            onClick={handleReset}
            className="w-full justify-center md:w-auto"
          >
            Reset
          </Button>
        </div>

        {error ? (
          <div
            className="rounded-2xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive-foreground"
            role="alert"
          >
            {error}
          </div>
        ) : null}

        {isLoading ? (
          <div className="py-6 text-center text-sm text-muted-foreground" role="status">
            Loading comparison…
          </div>
        ) : comparison && visibleCategories.length > 0 ? (
          <div className="space-y-8">
            {visibleCategories.map((category) => {
              const metrics = new Set<string>();
              comparison.entries.forEach((entry) => {
                Object.keys(categoryStats(entry, category)).forEach((metricKey) =>
                  metrics.add(metricKey)
                );
              });
              const rows = Array.from(metrics);
              return (
                <div key={category} className="space-y-3">
                  <h3 className="text-lg font-semibold">
                    {formatCategoryLabel(category)}
                  </h3>
                  <Table>
                    <TableHeader>
                      <TableRow className="[&_th]:whitespace-nowrap">
                        <TableHead className="w-52">Metric</TableHead>
                        {fighterColumns.map((entry) => (
                          <TableHead key={`${category}-${entry.fighter_id}`}>
                            {entry.name}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {rows.map((metricKey) => (
                        <TableRow key={`${category}-${metricKey}`}>
                          <TableCell className="font-medium">
                            {formatMetricLabel(metricKey)}
                          </TableCell>
                          {fighterColumns.map((entry) => (
                            <TableCell
                              key={`${entry.fighter_id}-${category}-${metricKey}`}
                              className="font-mono text-sm"
                            >
                              {normaliseValue(categoryStats(entry, category)[metricKey])}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="py-6 text-center text-sm text-muted-foreground">
            Search for another fighter to kick off a side-by-side comparison.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
