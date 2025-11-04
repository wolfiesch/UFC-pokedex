import { useState, useEffect, useCallback } from "react";
import type { FighterDetail } from "@/lib/types";
import client from "@/lib/api-client";

interface UseFighterDetailsResult {
  details: FighterDetail | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

// Simple in-memory cache for fighter details
const detailsCache = new Map<string, FighterDetail>();

/**
 * Custom hook for lazy loading fighter details
 *
 * @param fighterId - The ID of the fighter to fetch
 * @param enabled - Whether to fetch the data (set to true on hover)
 * @returns Fighter details, loading state, error state, and refetch function
 *
 * @example
 * ```tsx
 * const [isHovered, setIsHovered] = useState(false);
 * const { details, isLoading, error } = useFighterDetails(fighter.fighter_id, isHovered);
 *
 * // Use details.fight_history to show last fight, streak, etc.
 * ```
 */
export function useFighterDetails(
  fighterId: string,
  enabled: boolean
): UseFighterDetailsResult {
  const [details, setDetails] = useState<FighterDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchDetails = useCallback(async () => {
    // Don't fetch if disabled or already have data
    if (!enabled || details !== null) {
      return;
    }

    // Check cache first
    const cached = detailsCache.get(fighterId);
    if (cached) {
      setDetails(cached);
      return;
    }

    // Fetch from API
    setIsLoading(true);
    setError(null);

    try {
      const { data, error: apiError } = await client.GET("/fighters/{fighter_id}", {
        params: {
          path: {
            fighter_id: fighterId,
          },
        },
      });

      if (apiError || !data) {
        throw new Error("Failed to fetch fighter details");
      }

      // Cache the result
      detailsCache.set(fighterId, data as FighterDetail);

      setDetails(data as FighterDetail);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to fetch fighter details"));
    } finally {
      setIsLoading(false);
    }
  }, [fighterId, enabled, details]);

  // Fetch details when enabled becomes true
  useEffect(() => {
    if (enabled) {
      fetchDetails();
    }
  }, [enabled, fetchDetails]);

  const refetch = useCallback(() => {
    // Clear cached data and refetch
    detailsCache.delete(fighterId);
    setDetails(null);
    fetchDetails();
  }, [fighterId, fetchDetails]);

  return {
    details,
    isLoading,
    error,
    refetch,
  };
}

/**
 * Clear the details cache (useful for testing or when data becomes stale)
 */
export function clearDetailsCache(): void {
  detailsCache.clear();
}

/**
 * Preload fighter details (useful for optimistic loading)
 */
export async function preloadFighterDetails(fighterId: string): Promise<void> {
  if (detailsCache.has(fighterId)) {
    return; // Already cached
  }

  try {
    const { data, error } = await client.GET("/fighters/{fighter_id}", {
      params: {
        path: {
          fighter_id: fighterId,
        },
      },
    });

    if (!error && data) {
      detailsCache.set(fighterId, data as FighterDetail);
    }
  } catch (err) {
    // Silently fail preloading
    console.error(`Failed to preload fighter ${fighterId}:`, err);
  }
}
