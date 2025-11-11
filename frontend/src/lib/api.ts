/**
 * API client functions
 *
 * This module provides high-level API functions that wrap the type-safe OpenAPI client.
 * All functions use the auto-generated types from the OpenAPI schema.
 *
 * Migration note: This file has been refactored to use api-client.ts instead of
 * manual fetch calls and normalization. The function signatures remain the same
 * for backwards compatibility.
 *
 * @module api
 */

import type {
  FavoriteCollectionCreatePayload,
  FavoriteCollectionDetail,
  FavoriteCollectionListResponse,
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
import { resolveApiBaseUrl } from "./resolve-api-base-url";

const DEFAULT_CLIENT_API_BASE_URL = "http://localhost:8000";

/**
 * Type guard to check if error response has a status code
 */
function hasStatusCode(error: unknown): error is { status: number } {
  return (
    typeof error === "object" &&
    error !== null &&
    "status" in error &&
    typeof (error as { status: unknown }).status === "number"
  );
}

/**
 * Extract status code from error response safely
 *
 * @param error - Error object from openapi-fetch
 * @returns HTTP status code or 500 if unavailable
 */
function getStatusCode(error: unknown): number {
  return hasStatusCode(error) ? error.status : 500;
}

/**
 * Extract error detail message safely
 *
 * @param error - Error object from openapi-fetch
 * @returns Error detail string or undefined
 */
function getErrorDetail(error: unknown): string | undefined {
  if (typeof error === "object" && error !== null && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    return typeof detail === "string" ? detail : undefined;
  }
  return undefined;
}

/**
 * Helper to throw standardized API errors
 *
 * @param error - Error from openapi-fetch
 * @param defaultMessage - Fallback error message
 * @throws {ApiError} Always throws with structured error information
 */
function throwApiError(
  error: unknown,
  defaultMessage: string,
  context?: string
): never {
  const statusCode = getStatusCode(error);
  const detail = getErrorDetail(error);

  throw new ApiError(detail || defaultMessage, {
    statusCode,
    detail,
    context,
  });
}

/**
 * Helper to handle 404 errors with specific NotFoundError
 *
 * @param error - Error from openapi-fetch
 * @param resourceType - Type of resource (e.g., "Fighter", "Collection")
 * @param notFoundMessage - Specific message for 404 case
 * @param defaultMessage - Fallback error message for non-404 errors
 * @throws {NotFoundError} For 404 status codes
 * @throws {ApiError} For all other error status codes
 */
function throwApiErrorWithNotFound(
  error: unknown,
  resourceType: string,
  notFoundMessage: string,
  defaultMessage: string,
  context?: string
): never {
  const statusCode = getStatusCode(error);

  if (statusCode === 404) {
    throw new NotFoundError(resourceType, notFoundMessage);
  }

  throwApiError(error, defaultMessage, context);
}

/**
 * Get the API base URL from environment variables with proper URL resolution
 *
 * Uses resolveApiBaseUrl utility to handle URL parsing, scheme inference,
 * and validation with helpful error messages.
 *
 * @returns The configured API base URL or default localhost
 */
export function getApiBaseUrl(): string {
  return resolveApiBaseUrl(
    process.env.NEXT_PUBLIC_API_BASE_URL,
    DEFAULT_CLIENT_API_BASE_URL
  );
}

/**
 * Fetch a paginated list of fighters with optional streak information
 *
 * @param limit - Number of fighters per page (default: 20)
 * @param offset - Pagination offset (default: 0)
 * @returns Promise resolving to paginated fighters response
 * @throws {ApiError} If the request fails
 *
 * @example
 * ```ts
 * const fighters = await getFighters(20, 0);
 * console.log(fighters.fighters); // Array of fighter data
 * console.log(fighters.total);    // Total count
 * ```
 */
export async function getFighters(
  limit = 20,
  offset = 0
) {
  const { data, error } = await client.GET("/fighters/", {
    params: {
      query: {
        limit,
        offset,
        include_streak: true,
        streak_window: 6,
      },
    },
  });

  if (error) {
    throwApiError(error, "Failed to fetch fighters");
  }

  if (!data) {
    throw new ApiError("No data returned from API", { statusCode: 500 });
  }

  return data;
}

/**
 * Search fighters with multiple filter options
 *
 * @param query - Search query string (fighter name, nickname, etc.)
 * @param stance - Filter by stance (e.g., "Orthodox", "Southpaw")
 * @param division - Filter by weight division
 * @param championStatusFilters - Array of champion status filters
 * @param streakType - Filter by streak type ("win" or "loss")
 * @param minStreakCount - Minimum number of consecutive wins/losses
 * @param limit - Number of results per page (default: 20)
 * @param offset - Pagination offset (default: 0)
 * @returns Promise resolving to paginated search results
 * @throws {ApiError} If the search request fails
 *
 * @example
 * ```ts
 * // Search for lightweight fighters with win streaks
 * const results = await searchFighters(
 *   "",
 *   null,
 *   "Lightweight",
 *   [],
 *   "win",
 *   3,
 *   20,
 *   0
 * );
 * ```
 */
export async function searchFighters(
  query: string,
  stance: string | null = null,
  division: string | null = null,
  nationality: string | null = null,
  championStatusFilters: string[] = [],
  streakType: "win" | "loss" | null = null,
  minStreakCount: number | null = null,
  limit = 20,
  offset = 0
) {
  const trimmed = query.trim();

  // Build query parameters dynamically
  const queryParams: Record<string, string | number | string[]> = {
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
  if (nationality && nationality.length > 0) {
    queryParams.nationality = nationality;
  }
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
    throwApiError(error, "Search failed");
  }

  if (!data) {
    throw new ApiError("No data returned from search", { statusCode: 500 });
  }

  return data;
}

/**
 * Get a random fighter from the database
 *
 * @returns Promise resolving to a random fighter's basic information
 * @throws {ApiError} If the request fails
 *
 * @example
 * ```ts
 * const randomFighter = await getRandomFighter();
 * console.log(randomFighter.name);
 * ```
 */
export async function getRandomFighter() {
  const { data, error } = await client.GET("/fighters/random");

  if (error) {
    throwApiError(error, "Failed to fetch random fighter");
  }

  if (!data) {
    throw new ApiError("No fighter data returned", { statusCode: 500 });
  }

  return data;
}

/**
 * Get detailed information for a specific fighter including fight history
 *
 * @param fighterId - Unique fighter identifier
 * @returns Promise resolving to complete fighter profile
 * @throws {NotFoundError} If fighter with given ID doesn't exist
 * @throws {ApiError} If the request fails for other reasons
 *
 * @example
 * ```ts
 * const fighter = await getFighter("abc123");
 * console.log(fighter.name);
 * console.log(fighter.record);
 * console.log(fighter.fight_history);
 * ```
 */
export async function getFighter(fighterId: string) {
  const { data, error } = await client.GET("/fighters/{fighter_id}", {
    params: {
      path: {
        fighter_id: fighterId,
      },
    },
  });

  if (error) {
    throwApiErrorWithNotFound(
      error,
      "Fighter",
      `Fighter with ID "${fighterId}" not found`,
      "Failed to fetch fighter"
    );
  }

  if (!data) {
    throw new ApiError("No fighter data returned", { statusCode: 500 });
  }

  return data;
}

/**
 * Get global statistics summary with key performance indicators
 *
 * @returns Promise resolving to stats summary with metrics array
 * @throws {ApiError} If the request fails
 *
 * @example
 * ```ts
 * const stats = await getStatsSummary();
 * stats.metrics.forEach(metric => {
 *   console.log(`${metric.label}: ${metric.value}`);
 * });
 * ```
 */
export async function getStatsSummary() {
  const { data, error } = await client.GET("/stats/summary");

  if (error) {
    throwApiError(error, "Unable to load stats summary metrics", "stats_summary");
  }

  if (!data) {
    throw new ApiError("No stats data returned", {
      statusCode: 500,
      context: "stats_summary",
    });
  }

  return data;
}

/**
 * Get fighter leaderboards ranked by various metrics
 *
 * @returns Promise resolving to leaderboards for different stat categories
 * @throws {ApiError} If the request fails
 *
 * @example
 * ```ts
 * const leaderboards = await getStatsLeaderboards();
 * leaderboards.leaderboards.forEach(board => {
 *   console.log(`${board.title}:`);
 *   board.entries.forEach(entry => {
 *     console.log(`  ${entry.fighter_name}: ${entry.metric_value}`);
 *   });
 * });
 * ```
 */
export async function getStatsLeaderboards() {
  const { data, error } = await client.GET("/stats/leaderboards");

  if (error) {
    throwApiError(error, "Unable to load stats leaderboards", "stats_leaderboards");
  }

  if (!data) {
    throw new ApiError("No leaderboard data returned", {
      statusCode: 500,
      context: "stats_leaderboards",
    });
  }

  return data;
}

/**
 * Get statistics trends over time for time-series visualizations
 *
 * @returns Promise resolving to trend data with time series points
 * @throws {ApiError} If the request fails
 *
 * @example
 * ```ts
 * const trends = await getStatsTrends();
 * trends.trends.forEach(series => {
 *   console.log(`${series.label}:`);
 *   series.points.forEach(point => {
 *     console.log(`  ${point.timestamp}: ${point.value}`);
 *   });
 * });
 * ```
 */
export async function getStatsTrends() {
  const { data, error } = await client.GET("/stats/trends");

  if (error) {
    throwApiError(error, "Unable to load stats trends", "stats_trends");
  }

  if (!data) {
    throw new ApiError("No trend data returned", {
      statusCode: 500,
      context: "stats_trends",
    });
  }

  return data;
}

/**
 * Get all favorite collections for a specific user
 *
 * @param userId - Unique user identifier
 * @returns Promise resolving to list of user's collections
 * @throws {ApiError} If the request fails
 *
 * @example
 * ```ts
 * const collections = await getFavoriteCollections("user123");
 * collections.collections.forEach(collection => {
 *   console.log(`${collection.title} (${collection.stats?.total_fighters} fighters)`);
 * });
 * ```
 */
export async function getFavoriteCollections(
  userId: string
) {
  const { data, error } = await client.GET("/favorites/collections", {
    params: {
      query: {
        user_id: userId,
      },
    },
  });

  if (error) {
    throwApiError(error, "Failed to fetch collections");
  }

  if (!data) {
    throw new ApiError("No collection data returned", { statusCode: 500 });
  }

  // Map backend response to frontend types - backend uses 'id', frontend expects 'collection_id'
  return {
    total: data.total,
    collections: data.collections.map((collection) => ({
      ...collection,
      collection_id: collection.id,
    })),
  } as FavoriteCollectionListResponse;
}

/**
 * Get detailed information for a specific favorite collection
 *
 * @param collectionId - Unique collection identifier
 * @param userId - Optional user ID for authorization check
 * @returns Promise resolving to collection details with entries
 * @throws {NotFoundError} If collection doesn't exist
 * @throws {ApiError} If the request fails for other reasons
 *
 * @example
 * ```ts
 * const collection = await getFavoriteCollectionDetail(42, "user123");
 * console.log(`${collection.title}: ${collection.entries.length} fighters`);
 * ```
 */
export async function getFavoriteCollectionDetail(
  collectionId: number,
  userId?: string
) {
  const queryParams: Record<string, string> = {};
  if (userId && userId.trim().length > 0) {
    queryParams.user_id = userId;
  }

  const { data, error } = await client.GET(
    "/favorites/collections/{collection_id}",
    {
      params: {
        path: {
          collection_id: collectionId,
        },
        query: Object.keys(queryParams).length > 0 ? queryParams : undefined,
      },
    }
  );

  if (error) {
    throwApiErrorWithNotFound(
      error,
      "FavoriteCollection",
      `Collection ${collectionId} not found`,
      "Failed to fetch collection"
    );
  }

  if (!data) {
    throw new ApiError("No collection data returned", { statusCode: 500 });
  }

  // Map backend response to frontend types - backend uses 'id', frontend expects 'collection_id'
  return {
    ...data,
    collection_id: data.id,
    entries: data.entries?.map((entry) => ({
      ...entry,
      entry_id: entry.id,
      collection_id: data.id,
    })) ?? [],
  } as FavoriteCollectionDetail;
}

/**
 * Create a new favorite collection for a user
 *
 * @param payload - Collection creation data (title, description, etc.)
 * @returns Promise resolving to the newly created collection
 * @throws {ApiError} If creation fails (e.g., validation error)
 *
 * @example
 * ```ts
 * const newCollection = await createFavoriteCollection({
 *   user_id: "user123",
 *   title: "My Favorites",
 *   description: "Top fighters",
 *   is_public: false
 * });
 * console.log(`Created collection: ${newCollection.id}`);
 * ```
 */
export async function createFavoriteCollection(
  payload: FavoriteCollectionCreatePayload
) {
  const { data, error } = await client.POST("/favorites/collections", {
    body: payload,
  });

  if (error) {
    throwApiError(error, "Failed to create collection");
  }

  if (!data) {
    throw new ApiError("No collection data returned", { statusCode: 500 });
  }

  // Map backend response to frontend types - backend uses 'id', frontend expects 'collection_id'
  return {
    ...data,
    collection_id: data.id,
    entries: data.entries?.map((entry) => ({
      ...entry,
      entry_id: entry.id,
      collection_id: data.id,
    })) ?? [],
  } as FavoriteCollectionDetail;
}

/**
 * Add a fighter to a favorite collection
 *
 * @param collectionId - Target collection identifier
 * @param payload - Entry creation data (fighter_id, notes, tags, etc.)
 * @param userId - Optional user ID for authorization check
 * @returns Promise resolving to the newly created entry
 * @throws {ApiError} If adding fails (e.g., duplicate fighter)
 *
 * @example
 * ```ts
 * const entry = await addFavoriteEntry(42, {
 *   fighter_id: "abc123",
 *   notes: "Great striker",
 *   tags: ["knockout-artist"]
 * }, "user123");
 * ```
 */
export async function addFavoriteEntry(
  collectionId: number,
  payload: FavoriteEntryCreatePayload,
  userId?: string
) {
  const queryParams: Record<string, string> = {};
  if (userId && userId.trim().length > 0) {
    queryParams.user_id = userId;
  }

  const { data, error } = await client.POST(
    "/favorites/collections/{collection_id}/entries",
    {
      params: {
        path: {
          collection_id: collectionId,
        },
        query: Object.keys(queryParams).length > 0 ? queryParams : undefined,
      },
      body: payload,
    }
  );

  if (error) {
    throwApiError(error, "Failed to add favorite");
  }

  if (!data) {
    throw new ApiError("No entry data returned", { statusCode: 500 });
  }

  // Map backend response to frontend types - backend uses 'id', frontend expects 'entry_id'
  return {
    ...data,
    entry_id: data.id,
    collection_id: collectionId,
  } as FavoriteEntry;
}

/**
 * Reorder entries within a favorite collection
 *
 * @param collectionId - Target collection identifier
 * @param payload - Reorder instructions (entry IDs with new positions)
 * @param userId - Optional user ID for authorization check
 * @returns Promise resolving to updated collection with reordered entries
 * @throws {ApiError} If reordering fails
 *
 * @example
 * ```ts
 * const updated = await reorderFavoriteEntries(42, {
 *   entry_order: [5, 2, 1, 3, 4]
 * }, "user123");
 * ```
 */
export async function reorderFavoriteEntries(
  collectionId: number,
  payload: FavoriteEntryReorderPayload,
  userId?: string
) {
  const queryParams: Record<string, string> = {};
  if (userId && userId.trim().length > 0) {
    queryParams.user_id = userId;
  }

  const { data, error } = await client.POST(
    "/favorites/collections/{collection_id}/entries/reorder",
    {
      params: {
        path: {
          collection_id: collectionId,
        },
        query: Object.keys(queryParams).length > 0 ? queryParams : undefined,
      },
      body: payload,
    }
  );

  if (error) {
    throwApiError(error, "Failed to reorder entries");
  }

  if (!data) {
    throw new ApiError("No collection data returned", { statusCode: 500 });
  }

  // Map backend response to frontend types - backend uses 'id', frontend expects 'collection_id'
  return {
    ...data,
    collection_id: data.id,
    entries: data.entries?.map((entry) => ({
      ...entry,
      entry_id: entry.id,
      collection_id: data.id,
    })) ?? [],
  } as FavoriteCollectionDetail;
}

/**
 * Update an existing favorite entry's metadata
 *
 * @param collectionId - Parent collection identifier
 * @param entryId - Target entry identifier
 * @param payload - Update data (notes, tags, metadata)
 * @param userId - Optional user ID for authorization check
 * @returns Promise resolving to updated entry
 * @throws {ApiError} If update fails
 *
 * @example
 * ```ts
 * const updated = await updateFavoriteEntry(42, 7, {
 *   notes: "Updated analysis",
 *   tags: ["striker", "champion"]
 * }, "user123");
 * ```
 */
export async function updateFavoriteEntry(
  collectionId: number,
  entryId: number,
  payload: FavoriteEntryUpdatePayload,
  userId?: string
) {
  const queryParams: Record<string, string> = {};
  if (userId && userId.trim().length > 0) {
    queryParams.user_id = userId;
  }

  const { data, error } = await client.PATCH(
    "/favorites/collections/{collection_id}/entries/{entry_id}",
    {
      params: {
        path: {
          collection_id: collectionId,
          entry_id: entryId,
        },
        query: Object.keys(queryParams).length > 0 ? queryParams : undefined,
      },
      body: payload,
    }
  );

  if (error) {
    throwApiError(error, "Failed to update entry");
  }

  if (!data) {
    throw new ApiError("No entry data returned", { statusCode: 500 });
  }

  // Map backend response to frontend types - backend uses 'id', frontend expects 'entry_id'
  return {
    ...data,
    entry_id: data.id,
    collection_id: collectionId,
  } as FavoriteEntry;
}

/**
 * Delete a fighter entry from a favorite collection
 *
 * @param collectionId - Parent collection identifier
 * @param entryId - Target entry identifier to delete
 * @param userId - Optional user ID for authorization check
 * @returns Promise that resolves when deletion completes
 * @throws {ApiError} If deletion fails
 *
 * @example
 * ```ts
 * await deleteFavoriteEntry(42, 7, "user123");
 * console.log("Entry deleted successfully");
 * ```
 */
export async function deleteFavoriteEntry(
  collectionId: number,
  entryId: number,
  userId?: string
) {
  const queryParams: Record<string, string> = {};
  if (userId && userId.trim().length > 0) {
    queryParams.user_id = userId;
  }

  const { error } = await client.DELETE(
    "/favorites/collections/{collection_id}/entries/{entry_id}",
    {
      params: {
        path: {
          collection_id: collectionId,
          entry_id: entryId,
        },
        query: Object.keys(queryParams).length > 0 ? queryParams : undefined,
      },
    }
  );

  if (error) {
    throwApiError(error, "Failed to delete entry");
  }
}

/**
 * Get fight network graph data for visualization
 *
 * @param params - Query parameters for filtering graph (division, years, limit)
 * @returns Promise resolving to graph data with nodes and links
 * @throws {ApiError} If the request fails
 *
 * @example
 * ```ts
 * const graph = await getFightGraph({
 *   division: "Lightweight",
 *   startYear: 2020,
 *   endYear: 2024,
 *   limit: 100
 * });
 * console.log(`Graph has ${graph.nodes.length} fighters`);
 * console.log(`Graph has ${graph.links.length} connections`);
 * ```
 */
export async function getFightGraph(
  params: FightGraphQueryParams = {}
) {
  const queryParams: Record<string, string | number | boolean> = {};

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
    throwApiError(error, "Failed to fetch fight graph");
  }

  if (!data) {
    throw new ApiError("No graph data returned", { statusCode: 500 });
  }

  return data;
}

/**
 * Compare multiple fighters side-by-side with statistical analysis
 *
 * @param fighterIds - Array of fighter IDs to compare (minimum 2 required)
 * @returns Promise resolving to comparison data for all fighters
 * @throws {ApiError} If fewer than 2 fighter IDs provided or request fails
 *
 * @example
 * ```ts
 * const comparison = await compareFighters(["abc123", "def456", "ghi789"]);
 * comparison.fighters.forEach(fighter => {
 *   console.log(`${fighter.name}: ${fighter.record}`);
 *   console.log(`  Striking accuracy: ${fighter.striking.accuracy}%`);
 * });
 * ```
 */
export async function compareFighters(
  fighterIds: string[]
) {
  if (fighterIds.length < 2) {
    throw new ApiError("Select at least two fighters to compare.", {
      statusCode: 400,
      detail: "Comparison requires at least two fighter IDs",
    });
  }

  const { data, error } = await client.GET("/fighters/compare", {
    params: {
      query: {
        fighter_ids: fighterIds.filter(Boolean),
      },
    },
  });

  if (error) {
    throwApiError(error, "Failed to compare fighters");
  }

  if (!data) {
    throw new ApiError("No comparison data returned", { statusCode: 500 });
  }

  return data;
}
