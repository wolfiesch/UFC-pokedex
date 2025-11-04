"use client";

import { useCallback, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import type { FighterDetail } from "@/lib/types";
import { getFighter } from "@/lib/api";
import type { ApiError } from "@/lib/errors";

/**
 * Hook that retrieves a single fighter profile by identifier. The TanStack Query
 * cache keeps the profile warm so that navigating between comparison tabs or
 * revisiting the fighter card avoids redundant API calls.
 *
 * @param fighterId - Fighter identifier
 * @param initialData - Optional initial data from SSR/SSG (prevents refetch on mount)
 */
export function useFighter(fighterId: string, initialData?: FighterDetail) {
  const isEnabled = useMemo(() => fighterId.trim().length > 0, [fighterId]);

  const { data, status, error, refetch } = useQuery<FighterDetail, ApiError>({
    queryKey: ["fighter", fighterId],
    queryFn: () => getFighter(fighterId),
    enabled: isEnabled,
    initialData, // Hydrate from SSR/SSG data
    /**
     * Retry transient errors twice but do not retry 404s because the backend
     * already confirmed that the fighter does not exist.
     */
    retry: (failureCount, queryError) => {
      if (queryError.statusCode === 404) {
        return false;
      }
      return failureCount < 2;
    },
    staleTime: 1000 * 60 * 5,
  });

  const retry = useCallback(() => {
    void refetch();
  }, [refetch]);

  const fighter = data ?? null;
  const isLoading = status === "pending";
  const normalizedError = error ?? null;

  return { fighter, isLoading, error: normalizedError, retry };
}
