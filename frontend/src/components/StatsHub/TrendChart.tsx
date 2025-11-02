"use client";

import dynamic from "next/dynamic";
import { Suspense, type ReactNode } from "react";
import type { TrendSeries } from "@/lib/types";
import type { TrendChartInnerProps } from "./TrendChartInner";

const Chart = dynamic<TrendChartInnerProps>(
  () => import("./TrendChartInner"),
  {
    ssr: false,
    loading: () => (
      <p className="animate-pulse py-6 text-center text-sm text-slate-400" role="status">
        Preparing chart visualisation…
      </p>
    ),
  }
);

/**
 * Props interface for the trend chart wrapper. It mirrors the structure of the
 * leaderboard component, exposing helper flags for asynchronous states so that
 * the Stats Hub can provide consistent feedback for users.
 */
export interface TrendChartProps {
  /** Title displayed above the chart component. */
  title: string;
  /** Optional descriptive copy that explains the metric being visualised. */
  description?: string;
  /** Dataset composed of one or more time-series. */
  series: TrendSeries[];
  /** Enables a loading skeleton while data is fetched client-side. */
  isLoading?: boolean;
  /**
   * Optional error string used to display failure messaging without throwing an
   * exception inside the rendering tree.
   */
  error?: string | null;
}

/**
 * Wrapper component responsible for rendering trend data via the dynamically
 * imported Recharts implementation. It gracefully handles error, loading, and
 * empty states to ensure the UI remains informative regardless of data
 * availability.
 */
export default function TrendChart({
  title,
  description,
  series,
  isLoading = false,
  error,
}: TrendChartProps) {
  let content: ReactNode;

  if (error) {
    content = (
      <p className="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200" role="alert">
        {error}
      </p>
    );
  } else if (isLoading) {
    content = (
      <p className="animate-pulse py-6 text-center text-sm text-slate-400" role="status">
        Loading trend data…
      </p>
    );
  } else if (series.length === 0) {
    content = (
      <p className="py-6 text-center text-sm text-slate-400" role="status">
        No trend information is available for this metric yet.
      </p>
    );
  } else {
    content = (
      <Suspense
        fallback={
          <p className="animate-pulse py-6 text-center text-sm text-slate-400" role="status">
            Preparing chart visualisation…
          </p>
        }
      >
        <Chart series={series} />
      </Suspense>
    );
  }

  return (
    <section className="flex flex-col gap-3 rounded-lg border border-slate-800 bg-slate-950/80 p-5 shadow-lg">
      <header className="space-y-1">
        <h3 className="text-lg font-semibold text-pokedexYellow">{title}</h3>
        {description ? <p className="text-sm text-slate-400">{description}</p> : null}
      </header>
      {content}
    </section>
  );
}
