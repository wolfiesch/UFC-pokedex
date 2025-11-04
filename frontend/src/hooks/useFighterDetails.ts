import { useCallback, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { FighterDetail } from "@/lib/types";
import client from "@/lib/api-client";
import { getRegisteredQueryClient } from "@/lib/query-client-registry";

interface UseFighterDetailsResult {
  details: FighterDetail | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

const FIGHTER_DETAILS_QUERY_KEY = "fighter-details" as const;

const fighterDetailQueryOptions = {
  staleTime: 1000 * 60 * 5,
  gcTime: 1000 * 60 * 30,
};

const fetchFighterDetails = async (fighterId: string): Promise<FighterDetail> => {
  const { data, error: apiError } = await client.GET("/fighters/{fighter_id}", {
    params: {
      path: {
        fighter_id: fighterId,
      },
    },
  });

  if (!data || apiError) {
    throw new Error(`Failed to fetch fighter details for ${fighterId}`);
  }

  return data as FighterDetail;
};

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
  const queryClient = useQueryClient();
  const queryKey = useMemo(
    () => [FIGHTER_DETAILS_QUERY_KEY, fighterId] as const,
    [fighterId]
  );

  const {
    data,
    isLoading,
    error,
  } = useQuery({
    queryKey,
    queryFn: () => fetchFighterDetails(fighterId),
    enabled: Boolean(fighterId) && enabled,
    ...fighterDetailQueryOptions,
  });

  const refetch = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey });
  }, [queryClient, queryKey]);

  return {
    details: data ?? null,
    isLoading,
    error,
    refetch,
  };
}

/**
 * Clear the details cache (useful for testing or when data becomes stale)
 */
export function clearDetailsCache(): void {
  const client = getRegisteredQueryClient();
  if (!client) {
    console.warn(
      "[clearDetailsCache] No QueryClient registered. Cache was not cleared. " +
      "This may indicate that QueryProvider is not mounted or this is a server-side context."
    );
    return;
  }

  client.removeQueries({ queryKey: [FIGHTER_DETAILS_QUERY_KEY] });
}

/**
 * Preload fighter details (useful for optimistic loading)
 */
export async function preloadFighterDetails(fighterId: string): Promise<void> {
  const client = getRegisteredQueryClient();
  if (!client) {
    console.warn(
      "[preloadFighterDetails] No QueryClient registered. Preload was not performed. " +
      "This may indicate that QueryProvider is not mounted or this is a server-side context."
    );
    return;
  }

  try {
    await client.prefetchQuery({
      queryKey: [FIGHTER_DETAILS_QUERY_KEY, fighterId],
      queryFn: () => fetchFighterDetails(fighterId),
      ...fighterDetailQueryOptions,
    });
  } catch (err) {
    console.error(`Failed to preload fighter ${fighterId}:`, err);
  }
}
