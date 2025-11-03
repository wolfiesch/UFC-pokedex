"use client";

import { useCallback, useEffect, useState } from "react";

import type { FighterDetail } from "@/lib/types";
import { getApiBaseUrl } from "@/lib/api";
import { ApiError, NotFoundError } from "@/lib/errors";

export function useFighter(fighterId: string) {
  const [fighter, setFighter] = useState<FighterDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const load = useCallback(async (active: { current: boolean }) => {
    if (!fighterId) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${getApiBaseUrl()}/fighters/${fighterId}`, {
        cache: "no-store",
      });

      if (!active.current) return;

      if (response.status === 404) {
        const notFoundError = new NotFoundError(
          "Fighter",
          `Fighter with ID "${fighterId}" not found`
        );
        setError(notFoundError);
        setFighter(null);
        return;
      }

      if (!response.ok) {
        // Try to parse error response from backend
        try {
          const errorData = await response.json();
          const apiError = ApiError.fromResponse(errorData, response.status);
          setError(apiError);
        } catch {
          // Fallback if response is not JSON
          const apiError = new ApiError(
            `Failed to load fighter`,
            {
              statusCode: response.status,
              detail: `HTTP ${response.status} ${response.statusText}`,
            }
          );
          setError(apiError);
        }
        setFighter(null);
        return;
      }

      const data: FighterDetail = await response.json();
      if (active.current) {
        setFighter(data);
      }
    } catch (err) {
      if (!active.current) return;

      const apiError = err instanceof ApiError
        ? err
        : ApiError.fromNetworkError(
            err instanceof Error ? err : new Error("Unknown error")
          );

      setError(apiError);
      setFighter(null);
    } finally {
      if (active.current) {
        setIsLoading(false);
      }
    }
  }, [fighterId]);

  /**
   * Retry loading the fighter
   */
  const retry = useCallback(() => {
    const active = { current: true };
    void load(active);
  }, [load]);

  useEffect(() => {
    const active = { current: true };
    void load(active);
    return () => {
      active.current = false;
    };
  }, [load]);

  return { fighter, isLoading, error, retry };
}
