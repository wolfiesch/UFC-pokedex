"use client";

import { useMemo } from "react";
import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { getFightGraph } from "@/lib/api";
import type { ApiError } from "@/lib/errors";
import type { FightGraphQueryParams, FightGraphResponse } from "@/lib/types";

const FIGHT_GRAPH_STALE_TIME_MS = 1000 * 60 * 2;

export type UseFightGraphOptions = {
  /** Optional SSR/SSG payload to hydrate the query cache without refetching. */
  initialData?: FightGraphResponse | null;
  /** Set to false to skip the request entirely. */
  enabled?: boolean;
};

export type FightGraphQueryResult = UseQueryResult<
  FightGraphResponse,
  ApiError
>;

function buildQueryKey(filters: FightGraphQueryParams) {
  return [
    "fight-graph",
    filters.division ?? null,
    filters.startYear ?? null,
    filters.endYear ?? null,
    filters.limit ?? null,
    Boolean(filters.includeUpcoming),
  ] as const;
}

/**
 * Wrap TanStack Query with a domain-specific hook for the FightWeb graph. The
 * hook memoises the query key to ensure caching occurs per division/year/limit
 * combination and exposes the familiar query result contract.
 */
export function useFightGraph(
  filters: FightGraphQueryParams,
  options: UseFightGraphOptions = {},
): FightGraphQueryResult {
  const { initialData = null, enabled = true } = options;

  const queryKey = useMemo(() => buildQueryKey(filters), [filters]);

  return useQuery<FightGraphResponse, ApiError>({
    queryKey,
    queryFn: () => getFightGraph(filters),
    enabled,
    staleTime: FIGHT_GRAPH_STALE_TIME_MS,
    refetchOnWindowFocus: false,
    keepPreviousData: true,
    initialData: initialData ?? undefined,
  });
}
