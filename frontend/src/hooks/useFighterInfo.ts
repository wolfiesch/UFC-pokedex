"use client";

import { useQuery } from "@tanstack/react-query";
import client from "@/lib/api-client";
import type { FighterListItem } from "@/lib/types";

export interface FighterInfo {
  record?: string | null;
  current_rank?: number | null;
  current_rank_division?: string | null;
  is_current_champion?: boolean;
  is_former_champion?: boolean;
}

/**
 * Fetch minimal fighter information needed for event fight cards
 * (record, ranking, champion status)
 */
export function useFighterInfo(fighterId: string | null): {
  fighterInfo: FighterInfo | null;
  isLoading: boolean;
  error: unknown;
} {
  const query = useQuery({
    queryKey: ["fighter-info", fighterId],
    enabled: !!fighterId,
    queryFn: async () => {
      if (!fighterId) return null;

      const { data, error } = await client.GET("/fighters/{fighter_id}", {
        params: {
          path: {
            fighter_id: fighterId,
          },
        },
      });

      if (error) {
        throw error;
      }

      return data as FighterListItem;
    },
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
    gcTime: 1000 * 60 * 30, // Keep in cache for 30 minutes
    retry: 1,
  });

  const fighterInfo: FighterInfo | null = query.data ? {
    record: query.data.record,
    current_rank: query.data.current_rank,
    current_rank_division: query.data.current_rank_division,
    is_current_champion: query.data.is_current_champion,
    is_former_champion: query.data.is_former_champion,
  } : null;

  return {
    fighterInfo,
    isLoading: query.status === "pending",
    error: query.error ?? null,
  };
}
