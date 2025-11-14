"use client";

import { useQuery } from "@tanstack/react-query";

import {
  getFighterOddsChart,
  getFighterOddsHistory,
} from "@/lib/api";
import type { ApiError } from "@/lib/errors";
import type {
  FighterOddsChartResponse,
  FighterOddsHistoryResponse,
} from "@/types/odds";

const STALE_TIME_MS = 5 * 60 * 1000; // 5 minutes

export function useFighterOddsHistory(
  fighterId?: string,
  options?: { qualityMin?: string; limit?: number },
) {
  return useQuery<FighterOddsHistoryResponse, ApiError>({
    queryKey: [
      "odds",
      "history",
      fighterId,
      options?.qualityMin,
      options?.limit,
    ],
    queryFn: () => getFighterOddsHistory(fighterId!, options),
    enabled: Boolean(fighterId),
    staleTime: STALE_TIME_MS,
  });
}

export function useFighterOddsChart(
  fighterId?: string,
  options?: { limit?: number },
) {
  return useQuery<FighterOddsChartResponse, ApiError>({
    queryKey: ["odds", "chart", fighterId, options?.limit],
    queryFn: () => getFighterOddsChart(fighterId!, options),
    enabled: Boolean(fighterId),
    staleTime: STALE_TIME_MS,
  });
}
