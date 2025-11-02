"use client";

import { useEffect, useMemo, useState } from "react";

import { compareFighters, searchFighters } from "@/lib/api";
import { formatCategoryLabel, formatMetricLabel } from "@/lib/format";
import type { FighterComparisonEntry, FighterListItem } from "@/lib/types";

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
        const results = await searchFighters(trimmed, null, 10, 0);
        if (!cancelled) {
          setOptions(
            results.fighters
              .filter((item) => item.fighter_id !== primaryFighterId)
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

  const fighterColumns = useMemo(() => {
    return comparison?.entries ?? [];
  }, [comparison]);

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
    <section className="mt-10 space-y-4 rounded-3xl border border-slate-800 bg-slate-950/80 p-6 shadow-lg">
      <header className="space-y-1">
        <h2 className="text-xl font-semibold text-pokedexYellow">Compare Stats</h2>
        <p className="text-sm text-slate-400">
          Select another fighter to stack their metrics against {primaryFighterName || "this fighter"}.
        </p>
      </header>

      <div className="flex flex-col gap-3 md:flex-row">
        <div className="flex flex-1 flex-col gap-2">
          <label htmlFor="comparison-search" className="text-xs uppercase tracking-wide text-slate-500">
            Search fighters
          </label>
          <input
            id="comparison-search"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Start typing a fighter name..."
            className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-100 focus:border-pokedexYellow focus:outline-none"
          />
          {isSearching ? (
            <p className="text-xs text-slate-500">Searching…</p>
          ) : options.length > 0 ? (
            <ul className="space-y-1">
              {options.map((option) => (
                <li key={option.fighter_id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(option)}
                    className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-left text-sm text-slate-200 transition hover:border-pokedexYellow hover:text-pokedexYellow"
                  >
                    <span className="block font-semibold">{option.name}</span>
                    {option.nickname ? (
                      <span className="block text-xs text-slate-500">{option.nickname}</span>
                    ) : null}
                  </button>
                </li>
              ))}
            </ul>
          ) : query.trim().length >= 2 ? (
            <p className="text-xs text-slate-500">No fighters matched that search.</p>
          ) : null}
        </div>

        <div className="flex items-end">
          <button
            type="button"
            onClick={handleReset}
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 transition hover:border-pokedexYellow hover:text-pokedexYellow"
          >
            Reset
          </button>
        </div>
      </div>

      {error ? (
        <p className="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200" role="alert">
          {error}
        </p>
      ) : null}

      {isLoading ? (
        <p className="py-6 text-center text-sm text-slate-400" role="status">
          Loading comparison…
        </p>
      ) : comparison && visibleCategories.length > 0 ? (
        <div className="space-y-6">
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
                <h3 className="text-lg font-semibold text-slate-100">
                  {formatCategoryLabel(category)}
                </h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-800 text-left text-sm">
                    <thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-400">
                      <tr>
                        <th scope="col" className="px-4 py-3">
                          Metric
                        </th>
                        {fighterColumns.map((entry) => (
                          <th key={`${category}-${entry.fighter_id}`} scope="col" className="px-4 py-3">
                            {entry.name}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 text-slate-200">
                      {rows.map((metricKey) => (
                        <tr key={`${category}-${metricKey}`}>
                          <td className="px-4 py-3 font-semibold text-slate-300">
                            {formatMetricLabel(metricKey)}
                          </td>
                          {fighterColumns.map((entry) => (
                            <td key={`${entry.fighter_id}-${category}-${metricKey}`} className="px-4 py-3 font-mono text-sm">
                              {normaliseValue(categoryStats(entry, category)[metricKey])}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="py-6 text-center text-sm text-slate-500">
          Search for another fighter to kick off a side-by-side comparison.
        </p>
      )}
    </section>
  );
}
