"use client";

import Link from "next/link";
import type { LeaderboardEntry } from "@/lib/types";

/**
 * Props describing the configuration for a leaderboard table instance. Each
 * table receives a set of ranked entries and optional metadata to drive
 * descriptive copy or support loading/error states.
 */
export interface LeaderboardTableProps {
  /** Title displayed above the leaderboard section. */
  title: string;
  /** Optional helper text to clarify the ranked metric. */
  description?: string;
  /**
   * Collection of ranked fighter entries. The order in the array determines the
   * displayed ranking (i.e. index + 1).
   */
  entries: LeaderboardEntry[];
  /** Column header label describing the metric being ranked. */
  metricLabel?: string;
  /** Flag used to toggle the loading placeholder state. */
  isLoading?: boolean;
  /** Optional error message displayed when data retrieval fails. */
  error?: string | null;
}

/**
 * Lightweight helper that renders the leaderboard content area depending on the
 * state provided through the component props. Extracted to keep the JSX tidy.
 */
function renderLeaderboardBody({
  entries,
  metricLabel,
}: Pick<LeaderboardTableProps, "entries" | "metricLabel">) {
  if (entries.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-slate-400" role="status">
        No leaderboard data available yet. Check back soon as new fights are
        processed.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-800 text-left text-sm">
        <thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-400">
          <tr>
            <th scope="col" className="px-4 py-3">
              Rank
            </th>
            <th scope="col" className="px-4 py-3">
              Fighter
            </th>
            <th scope="col" className="px-4 py-3 text-right">
              {metricLabel ?? "Score"}
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {entries.map((entry, index) => (
            <tr key={`${entry.fighter_id}-${index}`} className="hover:bg-slate-900/40">
              <td className="px-4 py-3 font-semibold text-slate-300">{index + 1}</td>
              <td className="px-4 py-3">
                {entry.detail_url ? (
                  <Link
                    href={entry.detail_url}
                    className="text-pokedexYellow transition hover:text-yellow-300"
                  >
                    <span className="sr-only">View fighter profile:</span>
                    {entry.fighter_name}
                  </Link>
                ) : (
                  <span>{entry.fighter_name}</span>
                )}
              </td>
              <td className="px-4 py-3 text-right font-mono font-semibold text-slate-100">
                {entry.metric_value.toLocaleString(undefined, {
                  maximumFractionDigits: 2,
                })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Accessible, composable leaderboard table tailored for the Stats Hub. It
 * exposes helper props for handling asynchronous states (loading, error, empty)
 * so the parent view can provide meaningful feedback to users.
 */
export default function LeaderboardTable({
  title,
  description,
  entries,
  metricLabel,
  isLoading = false,
  error,
}: LeaderboardTableProps) {
  return (
    <section className="flex flex-col gap-3 rounded-lg border border-slate-800 bg-slate-950/80 p-5 shadow-lg">
      <header className="space-y-1">
        <h3 className="text-lg font-semibold text-pokedexYellow">{title}</h3>
        {description ? (
          <p className="text-sm text-slate-400">{description}</p>
        ) : null}
      </header>

      {error ? (
        <p className="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200" role="alert">
          {error}
        </p>
      ) : isLoading ? (
        <p className="animate-pulse py-6 text-center text-sm text-slate-400" role="status">
          Loading leaderboard…
        </p>
      ) : (
        renderLeaderboardBody({ entries, metricLabel })
      )}
    </section>
  );
}
