"use client";

import { useQuery } from "@tanstack/react-query";

import client from "@/lib/api-client";
import type { FighterListItem, PaginatedFightersResponse } from "@/lib/types";

const LOOKUP_FLAG =
  process.env.NEXT_PUBLIC_FEATURE_FIGHTER_LOOKUP?.toLowerCase() === "true";

export type UseFighterLookupOptions = {
  /** Force-enable or disable the lookup regardless of the global flag. */
  enabled?: boolean;
  /** Limit passed through to the backend search query. Default keeps payloads tiny. */
  limit?: number;
};

export interface FighterLookupResult {
  fighterId: string | null;
  fighterName: string | null;
  isEnabled: boolean;
  isLoading: boolean;
  status: "idle" | "pending" | "error" | "success";
  error: unknown;
}

function extractBestMatch(
  payload: PaginatedFightersResponse | null,
  targetName: string,
): FighterListItem | null {
  const fighters = payload?.fighters ?? [];
  if (!fighters.length) {
    return null;
  }
  const normalized = targetName.toLowerCase();
  const exact = fighters.find(
    (fighter) => fighter.name.toLowerCase() === normalized,
  );
  return exact ?? fighters[0] ?? null;
}

/**
 * Resolve fighter IDs from loose name references when the canonical ID is
 * missing in upstream payloads. The search call is opt-in behind a feature
 * flag to avoid extra latency on sensitive surfaces.
 */
export function useFighterLookup(
  name: string | null | undefined,
  options: UseFighterLookupOptions = {},
): FighterLookupResult {
  const normalizedName = typeof name === "string" ? name.trim() : "";
  if (!LOOKUP_FLAG) {
    return {
      fighterId: null,
      fighterName: null,
      isEnabled: false,
      isLoading: false,
      status: "idle",
      error: null,
    };
  }

  const isFeatureEnabled = options.enabled ?? true;
  const isEnabled = normalizedName.length > 0 && isFeatureEnabled;

  const query = useQuery({
    queryKey: ["fighter-lookup", normalizedName, options.limit ?? 5],
    enabled: isEnabled,
    queryFn: async () => {
      const { data, error } = await client.GET("/search/", {
        params: {
          query: {
            q: normalizedName,
            limit: options.limit ?? 5,
            include_streak: false,
          },
        },
      });
      if (error) {
        throw error;
      }
      return data ?? null;
    },
    staleTime: 1000 * 60 * 10,
    gcTime: 1000 * 60 * 30,
    retry: false,
  });

  const match = extractBestMatch(query.data ?? null, normalizedName);

  return {
    fighterId: match?.fighter_id ?? null,
    fighterName: match?.name ?? null,
    isEnabled,
    isLoading: query.status === "pending",
    status: query.status,
    error: query.error ?? null,
  };
}
