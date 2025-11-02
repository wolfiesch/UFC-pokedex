import type { Metadata } from "next";
import StatsDisplay from "@/components/StatsDisplay";
import { LeaderboardTable, TrendChart } from "@/components/StatsHub";
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

/**
 * Transform the summary response into the object shape expected by the
 * `StatsDisplay` component, mapping human-readable labels to their numeric KPI
 * values.
 */
function formatSummaryMetrics(summary: StatsSummaryResponse | null) {
  if (!summary || summary.metrics.length === 0) {
    return null;
  }
  return summary.metrics.reduce<Record<string, number>>((accumulator, metric) => {
    accumulator[metric.label] = metric.value;
    return accumulator;
  }, {});
}

/**
 * Helper that surfaces any optional metric descriptions so the Stats Hub can
 * render contextual copy beneath the KPI cards.
 */
function extractMetricDetails(summary: StatsSummaryResponse | null) {
  if (!summary) {
    return [] as StatsSummaryResponse["metrics"];
  }
  return summary.metrics.filter((metric) => Boolean(metric.description));
}

/**
 * Safety wrapper to guard against null responses from the leaderboard endpoint
 * while preserving strict typing when data is available.
 */
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
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-10 px-6 py-12">
      <header className="space-y-3 text-center md:text-left">
        <p className="text-sm uppercase tracking-[0.2em] text-pokedexYellow">Analytics</p>
        <h1 className="text-3xl font-bold text-slate-50 md:text-4xl">Stats Hub</h1>
        <p className="text-base text-slate-300 md:max-w-2xl">
          Dive into platform-wide UFC fighter insights. Review high-impact KPIs,
          explore competitive leaderboards, and investigate how performance
          metrics evolve over time.
        </p>
        {formattedGeneratedAt ? (
          <p className="text-xs text-slate-500">Last updated: {formattedGeneratedAt}</p>
        ) : null}
      </header>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-slate-100">Summary KPIs</h2>
          <span className="text-xs uppercase tracking-widest text-slate-500">Overview</span>
        </div>
        {summaryError ? (
          <p className="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200" role="alert">
            {summaryError}
          </p>
        ) : summaryStats ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <StatsDisplay title="Key Indicators" stats={summaryStats} />
          </div>
        ) : (
          <p className="py-6 text-center text-sm text-slate-400" role="status">
            Summary metrics are currently unavailable.
          </p>
        )}

        {summaryDescriptions.length > 0 ? (
          <dl className="grid gap-4 rounded-lg border border-slate-800 bg-slate-950/80 p-5 text-sm text-slate-300 md:grid-cols-2">
            {summaryDescriptions.map((metric) => (
              <div key={metric.id}>
                <dt className="font-semibold text-slate-100">{metric.label}</dt>
                <dd>{metric.description}</dd>
              </div>
            ))}
          </dl>
        ) : null}
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-slate-100">Leaderboards</h2>
          <span className="text-xs uppercase tracking-widest text-slate-500">Competition</span>
        </div>
        {leaderboardsError ? (
          <p className="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200" role="alert">
            {leaderboardsError}
          </p>
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {leaderboardDefinitions.length > 0 ? (
              leaderboardDefinitions.map((leaderboard) => (
                <LeaderboardTable
                  key={leaderboard.metric_id}
                  title={leaderboard.title}
                  description={leaderboard.description}
                  entries={leaderboard.entries}
                  metricLabel="Score"
                />
              ))
            ) : (
              <p className="py-6 text-center text-sm text-slate-400 md:col-span-2" role="status">
                Leaderboard data has not been published yet.
              </p>
            )}
          </div>
        )}
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-slate-100">Trends</h2>
          <span className="text-xs uppercase tracking-widest text-slate-500">Trajectory</span>
        </div>
        {trendsError ? (
          <p className="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200" role="alert">
            {trendsError}
          </p>
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
          <p className="py-6 text-center text-sm text-slate-400" role="status">
            Historical trend data will appear once enough events are ingested.
          </p>
        )}
      </section>
    </div>
  );
}
