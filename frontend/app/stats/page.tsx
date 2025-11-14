import type { Metadata } from "next";

import StatsDisplay from "@/components/StatsDisplay";
import { LeaderboardTable, TrendChart } from "@/components/StatsHub";
import { Badge } from "@/components/ui/badge";
import {
  getStatsLeaderboards,
  getStatsSummary,
  getStatsTrends,
} from "@/lib/api";
import type {
  LeaderboardDefinition,
  StatsLeaderboardsResponse,
  StatsSummaryResponse,
  StatsTrendsResponse,
} from "@/lib/types";

export const metadata: Metadata = {
  title: "Stats Hub • UFC Fighter Pokedex",
  description:
    "Explore aggregated UFC fighter insights including KPIs, leaderboards, and historical trends.",
};

// Force dynamic rendering to avoid build-time API calls
export const dynamic = 'force-dynamic';

function formatSummaryMetrics(summary: StatsSummaryResponse | null) {
  if (!summary || summary.metrics.length === 0) {
    return null;
  }
  return summary.metrics.reduce<Record<string, number>>((accumulator, metric) => {
    accumulator[metric.label] = metric.value;
    return accumulator;
  }, {});
}

function extractMetricDetails(summary: StatsSummaryResponse | null) {
  if (!summary) {
    return [] as StatsSummaryResponse["metrics"];
  }
  return summary.metrics.filter((metric) => Boolean(metric.description));
}

function leaderboardsFromResponse(response: StatsLeaderboardsResponse | null) {
  if (!response) {
    return [] as LeaderboardDefinition[];
  }
  return response.leaderboards;
}

export default async function StatsHubPage() {
  const [summaryResult, leaderboardsResult, trendsResult] = await Promise.allSettled([
    getStatsSummary(),
    getStatsLeaderboards(),
    getStatsTrends(),
  ]);

  const summary: StatsSummaryResponse | null =
    summaryResult.status === "fulfilled" ? summaryResult.value : null;
  const summaryError =
    summaryResult.status === "rejected"
      ? summaryResult.reason instanceof Error
        ? summaryResult.reason.message
        : "Unable to load summary metrics."
      : null;

  const leaderboards: StatsLeaderboardsResponse | null =
    leaderboardsResult.status === "fulfilled" ? leaderboardsResult.value : null;
  const leaderboardsError =
    leaderboardsResult.status === "rejected"
      ? leaderboardsResult.reason instanceof Error
        ? leaderboardsResult.reason.message
        : "Unable to load leaderboards."
      : null;

  const trends: StatsTrendsResponse | null =
    trendsResult.status === "fulfilled" ? trendsResult.value : null;
  const trendsError =
    trendsResult.status === "rejected"
      ? trendsResult.reason instanceof Error
        ? trendsResult.reason.message
        : "Unable to load trend data."
      : null;

  const summaryStats = formatSummaryMetrics(summary);
  const summaryDescriptions = extractMetricDetails(summary);
  const leaderboardDefinitions = leaderboardsFromResponse(leaderboards);
  const generatedAt = summary?.generated_at ?? leaderboards?.generated_at ?? trends?.generated_at;
  const lastUpdatedDate = generatedAt ? new Date(generatedAt) : null;
  const formattedGeneratedAt =
    lastUpdatedDate && !Number.isNaN(lastUpdatedDate.getTime())
      ? lastUpdatedDate.toLocaleString()
      : null;

  return (
    <section className="container flex flex-col gap-12 py-12">
      <header className="space-y-4">
        <Badge variant="outline" className="w-fit tracking-[0.35em]">
          Analytics
        </Badge>
        <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">Stats Hub</h1>
        <p className="max-w-2xl text-lg text-muted-foreground">
          Dive into platform-wide UFC fighter insights. Review high-impact KPIs, explore
          competitive leaderboards, and investigate how metrics evolve over time.
        </p>
        {formattedGeneratedAt ? (
          <p className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
            Last updated: {formattedGeneratedAt}
          </p>
        ) : null}
      </header>

      <section className="space-y-6">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <h2 className="text-2xl font-semibold tracking-tight">Summary KPIs</h2>
          <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
            Overview
          </span>
        </div>
        {summaryError ? (
          <div
            className="rounded-3xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive-foreground"
            role="alert"
          >
            {summaryError}
          </div>
        ) : summaryStats ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <StatsDisplay title="Key Indicators" stats={summaryStats} />
          </div>
        ) : (
          <div className="py-6 text-center text-sm text-muted-foreground" role="status">
            Summary metrics are currently unavailable.
          </div>
        )}

        {summaryDescriptions.length > 0 ? (
          <dl className="grid gap-4 rounded-3xl border border-border bg-card/80 p-6 text-sm text-foreground/80 md:grid-cols-2">
            {summaryDescriptions.map((metric) => (
              <div key={metric.id}>
                <dt className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">
                  {metric.label}
                </dt>
                <dd className="mt-2">{metric.description}</dd>
              </div>
            ))}
          </dl>
        ) : null}
      </section>

      <section className="space-y-6">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <h2 className="text-2xl font-semibold tracking-tight">Leaderboards</h2>
          <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
            Competition
          </span>
        </div>
        {leaderboardsError ? (
          <div
            className="rounded-3xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive-foreground"
            role="alert"
          >
            {leaderboardsError}
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {leaderboardDefinitions.length > 0 ? (
              leaderboardDefinitions.map((leaderboard, index) => (
                <LeaderboardTable
                  key={`${leaderboard.metric_id}-${index}`}
                  title={leaderboard.title}
                  description={leaderboard.description}
                  entries={leaderboard.entries}
                  metricLabel="Score"
                />
              ))
            ) : (
              <div
                className="py-6 text-center text-sm text-muted-foreground md:col-span-2"
                role="status"
              >
                Leaderboard data has not been published yet.
              </div>
            )}
          </div>
        )}
      </section>

      <section className="space-y-6">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <h2 className="text-2xl font-semibold tracking-tight">Trends</h2>
          <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
            Trajectory
          </span>
        </div>
        {trendsError ? (
          <div
            className="rounded-3xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive-foreground"
            role="alert"
          >
            {trendsError}
          </div>
        ) : trends && trends.trends.length > 0 ? (
          <div className="grid gap-6 lg:grid-cols-2">
            {trends.trends.map((seriesGroup) => (
              <TrendChart
                key={`${seriesGroup.metric_id}-${seriesGroup.fighter_id ?? "all"}`}
                title={seriesGroup.label}
                description={`Tracking ${seriesGroup.label.toLowerCase()} over time.`}
                series={[seriesGroup]}
              />
            ))}
          </div>
        ) : (
          <div className="py-6 text-center text-sm text-muted-foreground" role="status">
            Historical trend data will appear once enough events are ingested.
          </div>
        )}
      </section>
    </section>
  );
}
