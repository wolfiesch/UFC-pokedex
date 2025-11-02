"use client";

import React from "react";
import clsx from "clsx";

import type { LeaderboardEntry } from "./types";

/**
 * Properties accepted by {@link LeaderboardCard}. The optional `highlightCount`
 * allows the consumer (and tests) to assert how many rows should receive a
 * stronger accent color.
 */
export type LeaderboardCardProps = {
  title: string;
  entries: LeaderboardEntry[];
  highlightCount?: number;
};

/**
 * A simple leaderboard widget used inside the Stats Hub. It renders entries in
 * rank order while surfacing the raw metric and a delta indicator.
 */
export function LeaderboardCard({ title, entries, highlightCount = 3 }: LeaderboardCardProps) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <header className="mb-3 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-pokedexYellow">{title}</h3>
        <span className="text-xs uppercase tracking-wide text-slate-400">Top performers</span>
      </header>
      <ol className="space-y-2">
        {entries.map((entry, index) => {
          const isHighlighted = index < highlightCount;
          const deltaText = typeof entry.delta === "number" ? `${(entry.delta * 100).toFixed(1)}%` : null;

          return (
            <li
              key={entry.fighterId}
              className={clsx(
                "flex items-center justify-between rounded-lg border px-3 py-2",
                isHighlighted
                  ? "border-pokedexYellow/60 bg-pokedexYellow/10"
                  : "border-slate-800 bg-slate-900"
              )}
            >
              <div>
                <p className="text-sm font-semibold text-slate-100">{entry.fighterName}</p>
                <p className="text-xs text-slate-400">{entry.metricLabel}</p>
              </div>
              <div className="text-right text-sm text-pokedexBlue">
                <span className="block font-mono">{(entry.metricValue * 100).toFixed(1)}%</span>
                {deltaText && <span className="text-xs text-emerald-400">▲ {deltaText}</span>}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
