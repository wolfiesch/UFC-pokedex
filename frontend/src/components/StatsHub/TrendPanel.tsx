"use client";

import React from "react";
import type { TrendSeries } from "./types";

/**
 * Helper that formats a numeric value with a configurable number of decimal
 * places. Keeping the formatting logic inside the component makes the vitest
 * assertions straightforward and deterministic.
 */
function formatValue(value: number, fractionDigits = 2): string {
  return value.toFixed(fractionDigits).replace(/\.0+$/, "");
}

export type TrendPanelProps = {
  title: string;
  series: TrendSeries[];
};

/**
 * TrendPanel renders a grid of sparkline-style summaries. We avoid charting
 * libraries in tests by printing the latest values and simple deltas.
 */
export function TrendPanel({ title, series }: TrendPanelProps) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <header className="mb-3">
        <h3 className="text-lg font-semibold text-pokedexYellow">{title}</h3>
        <p className="text-xs text-slate-400">Rolling three-fight averages</p>
      </header>
      <div className="grid gap-3 md:grid-cols-2">
        {series.map((trend) => {
          const latest = trend.points[trend.points.length - 1];
          const previous = trend.points[trend.points.length - 2];
          const delta = latest.value - previous.value;

          return (
            <article
              key={trend.fighterId}
              className="rounded-lg border border-slate-800 bg-slate-950/70 p-3"
            >
              <h4 className="text-sm font-semibold text-slate-100">{trend.fighterName}</h4>
              <p className="text-xs text-slate-400">{trend.metricLabel}</p>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-pokedexBlue">
                  {formatValue(latest.value)}
                </span>
                <span className="text-xs text-emerald-400">+{formatValue(delta)}</span>
              </div>
              <dl className="mt-2 grid grid-cols-2 gap-1 text-[10px] text-slate-400">
                {trend.points.map((point) => (
                  <div key={`${trend.fighterId}-${point.label}`}>
                    <dt className="uppercase tracking-wide">{point.label}</dt>
                    <dd className="text-slate-200">{formatValue(point.value)}</dd>
                  </div>
                ))}
              </dl>
            </article>
          );
        })}
      </div>
    </section>
  );
}
