/**
 * API client functions
 *
 * This module provides high-level API functions that wrap the type-safe OpenAPI client.
 * All functions use the auto-generated types from the OpenAPI schema.
 *
 * Migration note: This file has been refactored to use api-client.ts instead of
 * manual fetch calls and normalization. The function signatures remain the same
 * for backwards compatibility.
 */

import type {
  FavoriteActivityItem,
  FavoriteCollectionCreatePayload,
  FavoriteCollectionDetail,
  FavoriteCollectionListResponse,
  FavoriteCollectionSummary,
  FavoriteEntry,
  FavoriteEntryCreatePayload,
  FavoriteEntryReorderPayload,
  FavoriteEntryUpdatePayload,
  FightGraphQueryParams,
  FightGraphResponse,
  FighterComparisonResponse,
  FighterDetail,
  FighterListItem,
  PaginatedFightersResponse,
  StatsLeaderboardsResponse,
  StatsSummaryResponse,
  StatsTrendsResponse,
} from "./types";
import client from "./api-client";
import { ApiError, NotFoundError } from "./errors";

/**
 * Get the API base URL from environment variables
 */
export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

/**
 * Fetch a paginated list of fighters
 *
 * @param limit - Number of fighters per page
 * @param offset - Pagination offset
 */
export async function getFighters(
  limit = 20,
  offset = 0
): Promise<PaginatedFightersResponse> {
  const { data, error } = await client.GET("/fighters/", {
    params: {
      query: {
        limit,
        offset,
        include_streak: 1,
        streak_window: 6,
      },
    },
  });

  if (error) {
    throw new ApiError(error.detail || "Failed to fetch fighters", {
      statusCode: (error as any).status || 500,
      detail: error.detail,
    });
  }

  return data as PaginatedFightersResponse;
}

/**
 * Search fighters with filters
 *
 * @param query - Search query string
 * @param stance - Filter by stance
 * @param division - Filter by division
 * @param championStatusFilters - Filter by champion status
 * @param streakType - Filter by streak type (win/loss)
 * @param minStreakCount - Minimum streak count
 * @param limit - Number of results per page
 * @param offset - Pagination offset
 */
export async function searchFighters(
  query: string,
  stance: string | null = null,
  division: string | null = null,
  championStatusFilters: string[] = [],
  streakType: "win" | "loss" | null = null,
  minStreakCount: number | null = null,
  limit = 20,
  offset = 0
): Promise<PaginatedFightersResponse> {
  const trimmed = query.trim();

  // Build query parameters
  const queryParams: Record<string, any> = {
    limit,
    offset,
  };

  if (trimmed.length > 0) {
    queryParams.q = trimmed;
  }
  if (stance && stance.length > 0) {
    queryParams.stance = stance;
  }
  if (division && division.length > 0) {
    queryParams.division = division;
  }
  // Note: openapi-fetch handles array parameters automatically
  if (championStatusFilters.length > 0) {
    queryParams.champion_statuses = championStatusFilters;
  }
  if (streakType && minStreakCount !== null && minStreakCount > 0) {
    queryParams.streak_type = streakType;
    queryParams.min_streak_count = minStreakCount;
  }

  const { data, error } = await client.GET("/search/", {
    params: {
      query: queryParams,
    },
  });

  if (error) {
    throw new ApiError(error.detail || "Search failed", {
      statusCode: (error as any).status || 500,
      detail: error.detail,
    });
  }

  return data as PaginatedFightersResponse;
}

/**
 * Get a random fighter
 */
export async function getRandomFighter(): Promise<FighterListItem> {
  const { data, error } = await client.GET("/fighters/random");

  if (error) {
    throw new ApiError(error.detail || "Failed to fetch random fighter", {
      statusCode: (error as any).status || 500,
      detail: error.detail,
    });
  }

  return data as FighterListItem;
}

/**
 * Get detailed information for a specific fighter
 *
 * @param fighterId - Fighter ID
 */
export async function getFighter(fighterId: string): Promise<FighterDetail> {
  const { data, error } = await client.GET("/fighters/{fighter_id}", {
    params: {
      path: {
        fighter_id: fighterId,
      },
    },
  });

  if (error) {
    const statusCode = (error as any).status || 500;

    if (statusCode === 404) {
      throw new NotFoundError(
        "Fighter",
        `Fighter with ID "${fighterId}" not found`
      );
    }

    throw new ApiError(error.detail || "Failed to fetch fighter", {
      statusCode,
      detail: error.detail,
    });
  }

  return data as FighterDetail;
}

/**
 * Get global stats summary (KPIs)
 */
export async function getStatsSummary(init?: RequestInit): Promise<StatsSummaryResponse> {
  const { data, error } = await client.GET("/stats/summary");

  if (error) {
    throw new ApiError(error.detail || "Failed to fetch stats summary", {
      statusCode: (error as any).status || 500,
      detail: error.detail,
    });
  }

  return data as StatsSummaryResponse;
}

/**
 * Get fighter leaderboards
 */
export async function getStatsLeaderboards(
  init?: RequestInit
): Promise<StatsLeaderboardsResponse> {
  const { data, error } = await client.GET("/stats/leaderboards");

  if (error) {
    throw new ApiError(error.detail || "Failed to fetch leaderboards", {
      statusCode: (error as any).status || 500,
      detail: error.detail,
    });
  }

  return data as StatsLeaderboardsResponse;
}

/**
 * Get stats trends over time
 */
export async function getStatsTrends(init?: RequestInit): Promise<StatsTrendsResponse> {
  const { data, error } = await client.GET("/stats/trends");

  if (error) {
    throw new ApiError(error.detail || "Failed to fetch trends", {
      statusCode: (error as any).status || 500,
      detail: error.detail,
    });
  }

  return data as StatsTrendsResponse;
}

/**
 * Get all favorite collections for a user
 *
 * @param userId - User ID
 */
export async function getFavoriteCollections(
  userId: string,
  init?: RequestInit
): Promise<FavoriteCollectionListResponse> {
  const { data, error } = await client.GET("/favorites/collections", {
    params: {
      query: {
        user_id: userId,
      },
    },
  });

  if (error) {
    throw new ApiError(error.detail || "Failed to fetch collections", {
      statusCode: (error as any).status || 500,
      detail: error.detail,
    });
  }

  return data as FavoriteCollectionListResponse;
}

/**
 * Get detailed information for a specific collection
 *
 * @param collectionId - Collection ID
 * @param userId - Optional user ID for authorization
 */
export async function getFavoriteCollectionDetail(
  collectionId: number,
  userId?: string,
  init?: RequestInit
): Promise<FavoriteCollectionDetail> {
  const queryParams: Record<string, any> = {};
  if (userId && userId.trim().length > 0) {
    queryParams.user_id = userId;
  }

  const { data, error } = await client.GET("/favorites/collections/{collection_id}", {
    params: {
      path: {
        collection_id: collectionId,
      },
      query: Object.keys(queryParams).length > 0 ? queryParams : undefined,
    },
  });

  if (error) {
    const statusCode = (error as any).status || 500;

    if (statusCode === 404) {
      throw new NotFoundError(
        "FavoriteCollection",
        `Collection ${collectionId} not found`
      );
    }

    throw new ApiError(error.detail || "Failed to fetch collection", {
      statusCode,
      detail: error.detail,
    });
  }

  return data as FavoriteCollectionDetail;
}

/**
 * Create a new favorite collection
 *
 * @param payload - Collection creation data
 */
export async function createFavoriteCollection(
  payload: FavoriteCollectionCreatePayload,
  init?: RequestInit
): Promise<FavoriteCollectionDetail> {
  const { data, error } = await client.POST("/favorites/collections", {
    body: payload as any,
  });

  if (error) {
    throw new ApiError(error.detail || "Failed to create collection", {
      statusCode: (error as any).status || 500,
      detail: error.detail,
    });
  }

  return data as FavoriteCollectionDetail;
}

/**
 * Add a fighter to a collection
 *
 * @param collectionId - Collection ID
 * @param payload - Entry creation data
 * @param userId - Optional user ID for authorization
 */
export async function addFavoriteEntry(
  collectionId: number,
  payload: FavoriteEntryCreatePayload,
  userId?: string,
  init?: RequestInit
): Promise<FavoriteEntry> {
  const queryParams: Record<string, any> = {};
  if (userId && userId.trim().length > 0) {
    queryParams.user_id = userId;
  }

  const { data, error } = await client.POST("/favorites/collections/{collection_id}/entries", {
    params: {
      path: {
        collection_id: collectionId,
      },
      query: Object.keys(queryParams).length > 0 ? queryParams : undefined,
    },
    body: payload as any,
  });

  if (error) {
    throw new ApiError(error.detail || "Failed to add favorite", {
      statusCode: (error as any).status || 500,
      detail: error.detail,
    });
  }

  return data as FavoriteEntry;
}

/**
 * Reorder entries in a collection
 *
 * @param collectionId - Collection ID
 * @param payload - Reorder data
 * @param userId - Optional user ID for authorization
 */
export async function reorderFavoriteEntries(
  collectionId: number,
  payload: FavoriteEntryReorderPayload,
  userId?: string,
  init?: RequestInit
): Promise<FavoriteCollectionDetail> {
  const queryParams: Record<string, any> = {};
  if (userId && userId.trim().length > 0) {
    queryParams.user_id = userId;
  }

  const { data, error } = await client.POST("/favorites/collections/{collection_id}/entries/reorder", {
    params: {
      path: {
        collection_id: collectionId,
      },
      query: Object.keys(queryParams).length > 0 ? queryParams : undefined,
    },
    body: payload as any,
  });

  if (error) {
    throw new ApiError(error.detail || "Failed to reorder entries", {
      statusCode: (error as any).status || 500,
      detail: error.detail,
    });
  }

  return data as FavoriteCollectionDetail;
}

/**
 * Update a favorite entry
 *
 * @param collectionId - Collection ID
 * @param entryId - Entry ID
 * @param payload - Update data
 * @param userId - Optional user ID for authorization
 */
export async function updateFavoriteEntry(
  collectionId: number,
  entryId: number,
  payload: FavoriteEntryUpdatePayload,
  userId?: string,
  init?: RequestInit
): Promise<FavoriteEntry> {
  const queryParams: Record<string, any> = {};
  if (userId && userId.trim().length > 0) {
    queryParams.user_id = userId;
  }

  const { data, error } = await client.PATCH("/favorites/collections/{collection_id}/entries/{entry_id}", {
    params: {
      path: {
        collection_id: collectionId,
        entry_id: entryId,
      },
      query: Object.keys(queryParams).length > 0 ? queryParams : undefined,
    },
    body: payload as any,
  });

  if (error) {
    throw new ApiError(error.detail || "Failed to update entry", {
      statusCode: (error as any).status || 500,
      detail: error.detail,
    });
  }

  return data as FavoriteEntry;
}

/**
 * Delete a favorite entry
 *
 * @param collectionId - Collection ID
 * @param entryId - Entry ID
 * @param userId - Optional user ID for authorization
 */
export async function deleteFavoriteEntry(
  collectionId: number,
  entryId: number,
  userId?: string,
  init?: RequestInit
): Promise<void> {
  const queryParams: Record<string, any> = {};
  if (userId && userId.trim().length > 0) {
    queryParams.user_id = userId;
  }

  const { error } = await client.DELETE("/favorites/collections/{collection_id}/entries/{entry_id}", {
    params: {
      path: {
        collection_id: collectionId,
        entry_id: entryId,
      },
      query: Object.keys(queryParams).length > 0 ? queryParams : undefined,
    },
  });

  if (error) {
    throw new ApiError(error.detail || "Failed to delete entry", {
      statusCode: (error as any).status || 500,
      detail: error.detail,
    });
  }
}

/**
 * Get fight graph data
 *
 * @param params - Graph query parameters (division, year range, etc.)
 */
export async function getFightGraph(
  params: FightGraphQueryParams = {},
  init?: RequestInit
): Promise<FightGraphResponse> {
  const queryParams: Record<string, any> = {};

  if (params.division && params.division.trim().length > 0) {
    queryParams.division = params.division;
  }
  if (typeof params.startYear === "number") {
    queryParams.start_year = params.startYear;
  }
  if (typeof params.endYear === "number") {
    queryParams.end_year = params.endYear;
  }
  if (typeof params.limit === "number") {
    queryParams.limit = params.limit;
  }
  if (typeof params.includeUpcoming === "boolean") {
    queryParams.include_upcoming = params.includeUpcoming;
  }

  const { data, error } = await client.GET("/fightweb/graph", {
    params: {
      query: Object.keys(queryParams).length > 0 ? queryParams : undefined,
    },
  });

  if (error) {
    throw new ApiError(error.detail || "Failed to fetch fight graph", {
      statusCode: (error as any).status || 500,
      detail: error.detail,
    });
  }

  return data as FightGraphResponse;
}

/**
 * Compare multiple fighters
 *
 * @param fighterIds - Array of fighter IDs to compare
 */
export async function compareFighters(
  fighterIds: string[]
): Promise<FighterComparisonResponse> {
  if (fighterIds.length < 2) {
    throw new ApiError("Select at least two fighters to compare.", {
      statusCode: 400,
      detail: "Comparison requires at least two fighter IDs",
    });
  }

  const { data, error } = await client.GET("/fighters/compare", {
    params: {
      query: {
        fighter_ids: fighterIds,
      },
    },
  });

  if (error) {
    throw new ApiError(error.detail || "Failed to compare fighters", {
      statusCode: (error as any).status || 500,
      detail: error.detail,
    });
  }

  return data as FighterComparisonResponse;
}
