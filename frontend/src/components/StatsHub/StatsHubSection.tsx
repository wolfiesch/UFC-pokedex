"use client";

import React from "react";
import { LeaderboardCard } from "./LeaderboardCard";
import { TrendPanel } from "./TrendPanel";
import type { LeaderboardEntry, TrendSeries } from "./types";

export type StatsHubSectionProps = {
  leaderboardTitle: string;
  leaderboardEntries: LeaderboardEntry[];
  trendTitle: string;
  trendSeries: TrendSeries[];
};

/**
 * StatsHubSection composes the smaller widgets into a cohesive layout. Keeping
 * the container component lean allows the Vitest suite to render a single
 * component tree when verifying deterministic output.
 */
export function StatsHubSection({
  leaderboardTitle,
  leaderboardEntries,
  trendTitle,
  trendSeries,
}: StatsHubSectionProps) {
  return (
    <section className="grid gap-4 lg:grid-cols-2">
      <LeaderboardCard title={leaderboardTitle} entries={leaderboardEntries} />
      <TrendPanel title={trendTitle} series={trendSeries} />
    </section>
  );
}
