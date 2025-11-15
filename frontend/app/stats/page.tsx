import type { JSX } from "react";
import type { Metadata } from "next";

import StatsDisplay from "@/components/StatsDisplay";
import { LeaderboardTable, TrendChart } from "@/components/StatsHub";
import {
  DEFAULT_LEADERBOARD_CAPTION,
  DEFAULT_STATS_LEADERBOARD_METRICS,
  STAT_LEADERBOARD_CONFIG,
  STAT_LEADERBOARD_SECTIONS,
} from "@/components/StatsHub/metricConfig";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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

// For static export, allow graceful fallback when API is unavailable during build
// Uses Promise.allSettled to handle API failures gracefully

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
    getStatsLeaderboards({ metrics: DEFAULT_STATS_LEADERBOARD_METRICS }),
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
  const leaderboardsByMetric = new Map(
    leaderboardDefinitions.map((definition) => [definition.metric_id, definition]),
  );
  const leaderboardSectionBlocks = STAT_LEADERBOARD_SECTIONS.map((section) => {
    const sectionLeaderboards = section.metrics
      .map((metricId) => leaderboardsByMetric.get(metricId))
      .filter(Boolean) as LeaderboardDefinition[];
    if (sectionLeaderboards.length === 0) {
      return null;
    }
    return (
      <div key={section.id} className="space-y-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-xl font-semibold tracking-tight">{section.title}</h3>
            <p className="text-sm text-muted-foreground">{section.description}</p>
          </div>
          <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
            {section.id}
          </span>
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          {sectionLeaderboards.map((leaderboard) => {
            const metricConfig = STAT_LEADERBOARD_CONFIG[leaderboard.metric_id];
            return (
              <LeaderboardTable
                key={leaderboard.metric_id}
                title={metricConfig?.title ?? leaderboard.title}
                description={metricConfig?.description ?? leaderboard.description}
                entries={leaderboard.entries}
                metricLabel={metricConfig?.metricLabel ?? "Score"}
                caption={metricConfig?.caption ?? DEFAULT_LEADERBOARD_CAPTION}
              />
            );
          })}
        </div>
      </div>
    );
  }).filter((section): section is JSX.Element => Boolean(section));
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

      <Tabs defaultValue="summary" className="space-y-8">
        <TabsList className="flex w-full flex-wrap gap-2 rounded-3xl border border-border bg-card/70 p-2">
          <TabsTrigger value="summary" className="flex-1 rounded-2xl text-sm font-semibold">
            Summary
          </TabsTrigger>
          <TabsTrigger value="leaderboards" className="flex-1 rounded-2xl text-sm font-semibold">
            Leaderboards
          </TabsTrigger>
          <TabsTrigger value="trends" className="flex-1 rounded-2xl text-sm font-semibold">
            Trends
          </TabsTrigger>
        </TabsList>

        <TabsContent value="summary">
          <section className="space-y-6 rounded-3xl border border-border bg-card/60 p-6">
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
        </TabsContent>

        <TabsContent value="leaderboards">
          <section className="space-y-6">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <h2 className="text-2xl font-semibold tracking-tight">Leaderboards</h2>
              <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
                Competition
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              Includes fighters with ≥5 UFC fights by default. Lower the threshold to explore
              small-sample outliers when needed.
            </p>
            {leaderboardsError ? (
              <div
                className="rounded-3xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive-foreground"
                role="alert"
              >
                {leaderboardsError}
              </div>
            ) : leaderboardSectionBlocks.length > 0 ? (
              <div className="space-y-10">{leaderboardSectionBlocks}</div>
            ) : (
              <div
                className="rounded-3xl border border-border bg-card/60 p-6 text-center text-sm text-muted-foreground"
                role="status"
              >
                Leaderboard data has not been published yet.
              </div>
            )}
          </section>
        </TabsContent>

        <TabsContent value="trends">
          <section className="space-y-6 rounded-3xl border border-border bg-card/60 p-6">
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
        </TabsContent>
      </Tabs>
    </section>
  );
}
