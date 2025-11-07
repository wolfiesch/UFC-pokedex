import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import {
  getStatsLeaderboards,
  getStatsSummary,
  getStatsTrends,
} from "@/lib/api";
import { ApiError } from "@/lib/errors";
import type {
  StatsLeaderboardsResponse,
  StatsSummaryResponse,
  StatsTrendsResponse,
} from "@/lib/types";

/**
 * Convert an arbitrary error value into a user-friendly message. The helper ensures that
 * Stats Hub surfaces a descriptive error string regardless of whether the error originated
 * from the typed {@link ApiError} class or from an unexpected runtime failure.
 */
function resolveErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.getUserMessage();
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
}

export type StatsSummaryQueryResult = UseQueryResult<StatsSummaryResponse, ApiError> & {
  /** Derived, human-readable error string bound to Stats Hub summary widgets. */
  errorMessage: string | null;
};

/**
 * Fetch the Stats summary payload through TanStack Query while exposing a derived error message.
 * The query metadata marks the request context so shared logging/reporting can pinpoint failures.
 */
export function useStatsSummaryQuery(): StatsSummaryQueryResult {
  const query = useQuery<StatsSummaryResponse, ApiError>({
    queryKey: ["stats", "summary"],
    queryFn: getStatsSummary,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    retry: 1,
    meta: { context: "stats_summary" },
  });

  return {
    ...query,
    errorMessage: query.error
      ? resolveErrorMessage(query.error, "Unable to load stats summary metrics.")
      : null,
  };
}

export type StatsLeaderboardsQueryResult = UseQueryResult<
  StatsLeaderboardsResponse,
  ApiError
> & {
  /** Derived error string specifically for leaderboard call sites. */
  errorMessage: string | null;
};

/**
 * Retrieve leaderboard data with caching semantics tuned for frequently refreshed dashboards.
 * Consumers can reference {@link StatsLeaderboardsQueryResult.errorMessage} to present
 * contextual status banners.
 */
export function useStatsLeaderboardsQuery(): StatsLeaderboardsQueryResult {
  const query = useQuery<StatsLeaderboardsResponse, ApiError>({
    queryKey: ["stats", "leaderboards"],
    queryFn: getStatsLeaderboards,
    staleTime: 3 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    retry: 1,
    meta: { context: "stats_leaderboards" },
  });

  return {
    ...query,
    errorMessage: query.error
      ? resolveErrorMessage(query.error, "Unable to load stats leaderboards.")
      : null,
  };
}

export type StatsTrendsQueryResult = UseQueryResult<StatsTrendsResponse, ApiError> & {
  /** Human-readable message suitable for chart-level alerts when trend requests fail. */
  errorMessage: string | null;
};

/**
 * Request historical trend data and surface a friendly error message alongside the query state.
 * The query is configured with a modest stale time to keep dashboards responsive to updates
 * without overloading the API.
 */
export function useStatsTrendsQuery(): StatsTrendsQueryResult {
  const query = useQuery<StatsTrendsResponse, ApiError>({
    queryKey: ["stats", "trends"],
    queryFn: getStatsTrends,
    staleTime: 3 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    retry: 1,
    meta: { context: "stats_trends" },
  });

  return {
    ...query,
    errorMessage: query.error
      ? resolveErrorMessage(query.error, "Unable to load stats trends.")
      : null,
  };
}
