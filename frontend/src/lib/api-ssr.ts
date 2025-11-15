/**
 * Server-side API client for SSG/ISR
 * This module provides fetch functions optimized for static generation at build time.
 * Unlike the client-side api.ts, these functions:
 * - Use default Next.js caching behavior
 * - Don't include complex retry logic (build fails fast if API is down)
 * - Are designed to run in React Server Components only
 */

import type {
  FighterDetail,
  FighterListItem,
  PaginatedFightersResponse,
} from "./types";
import { resolveApiBaseUrl } from "./resolve-api-base-url";
import { getDefaultApiBaseUrl } from "./deployment-config";

/**
 * Default API base URL for server-side rendering contexts.
 *
 * Next.js executes server components during both the build step and runtime
 * (ISR).  In hosted environments there is no localhost backend, so the helper
 * switches to the public Railway deployment.  Local development still targets
 * the developer machine to preserve the fast feedback loop.
 */
const DEFAULT_SSR_API_BASE_URL: string = getDefaultApiBaseUrl(
  "http://localhost:8000",
);

function getApiBaseUrl(): string {
  // Default to localhost for local development, but allow environment overrides.
  // resolveApiBaseUrl normalizes the value (adds scheme, strips trailing slash).
  return resolveApiBaseUrl(
    process.env.NEXT_SSR_API_BASE_URL,
    DEFAULT_SSR_API_BASE_URL,
  );
}

const FETCH_TIMEOUT_MS = 4000;

/**
 * Fetch paginated fighters list for SSG
 * Used by home page static generation
 */
export async function getFightersSSR(
  limit = 20,
  offset = 0,
): Promise<PaginatedFightersResponse> {
  const apiUrl = getApiBaseUrl();
  const response = await fetch(
    `${apiUrl}/fighters/?limit=${limit}&offset=${offset}`,
    {
      // Cache for 60 seconds (1 minute)
      next: { revalidate: 60 },
    },
  );

  if (!response.ok) {
    throw new Error(
      `Failed to fetch fighters: ${response.status} ${response.statusText}`,
    );
  }

  return response.json();
}

/**
 * Fetch single fighter detail for SSG/ISR
 * Used by fighter detail page generation
 */
export async function getFighterSSR(fighterId: string): Promise<FighterDetail> {
  const apiUrl = getApiBaseUrl();
  const response = await fetch(`${apiUrl}/fighters/${fighterId}`, {
    // Cache for 5 minutes (300 seconds)
    // Stale-while-revalidate for 10 minutes
    next: { revalidate: 300 },
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Fighter not found: ${fighterId}`);
    }
    throw new Error(
      `Failed to fetch fighter: ${response.status} ${response.statusText}`,
    );
  }

  return response.json();
}

/**
 * Fetch all fighter IDs for generateStaticParams
 * Fetches all fighters, sorts by most recent fight date, returns top N
 */
export async function getAllFighterIdsSSR(
  topN = 500,
): Promise<Array<{ id: string }>> {
  const apiUrl = getApiBaseUrl();

  // Strategy: Fetch fighters in batches until we have all of them
  const allFighters: FighterListItem[] = [];
  const batchSize = 100; // Backend max limit (le=100 in Query validation)
  let offset = 0;
  let hasMore = true;

  while (hasMore) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

    try {
      const response = await fetch(
        `${apiUrl}/fighters/?limit=${batchSize}&offset=${offset}`,
        {
          next: { revalidate: false }, // Static at build time
          signal: controller.signal,
        },
      );

      if (!response.ok) {
        throw new Error(
          `Failed to fetch fighters batch: ${response.status} ${response.statusText}`,
        );
      }

      const data: PaginatedFightersResponse = await response.json();
      allFighters.push(...data.fighters);

      hasMore = data.has_more;
      offset += batchSize;
    } catch (error) {
      const isAbortError =
        error instanceof Error && error.name === "AbortError";

      const message = isAbortError
        ? `Timed out fetching fighters batch at offset ${offset}`
        : `Failed to fetch fighters batch at offset ${offset}: ${error}`;
      console.warn(message);

      if (allFighters.length === 0) {
        console.warn(
          "Skipping fighter prefetch – API unavailable during build. Falling back to ISR.",
        );
        break;
      }

      break;
    } finally {
      clearTimeout(timeoutId);
    }

    // Safety limit: don't fetch more than 10,000 fighters
    if (offset >= 10000) {
      break;
    }
  }

  // Sort by most recent fighters (those with complete data are likely more active)
  // Prioritize fighters with:
  // 1. Non-null division (active fighters)
  // 2. Non-null record (have fights)
  // 3. Alphabetically by name as fallback
  const sortedFighters = allFighters.sort((a, b) => {
    // Prioritize fighters with division
    if (a.division && !b.division) return -1;
    if (!a.division && b.division) return 1;

    // Then by name alphabetically
    return a.name.localeCompare(b.name);
  });

  // Take top N fighters
  return sortedFighters.slice(0, topN).map((fighter) => ({
    id: fighter.fighter_id,
  }));
}

/**
 * Fetch all event IDs for generateStaticParams
 * Returns all available events
 */
export async function getAllEventIdsSSR(): Promise<Array<{ id: string }>> {
  const apiUrl = getApiBaseUrl();

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

    const response = await fetch(`${apiUrl}/events/`, {
      next: { revalidate: false }, // Static at build time
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(
        `Failed to fetch events: ${response.status} ${response.statusText}`,
      );
    }

    const data = await response.json();
    const events = data.events || [];

    return events.map((event: { event_id: string }) => ({
      id: event.event_id,
    }));
  } catch (error) {
    console.warn("Failed to fetch events for static generation:", error);
    console.warn("Skipping event prefetch – API unavailable during build.");
    return [];
  }
}

/**
 * Fetch all division names for generateStaticParams
 * Returns list of available weight class divisions that have data
 */
export async function getAllDivisionNamesSSR(): Promise<
  Array<{ division: string }>
> {
  const apiUrl = getApiBaseUrl();

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

    const response = await fetch(`${apiUrl}/rankings/`, {
      next: { revalidate: false }, // Static at build time
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(
        `Failed to fetch divisions: ${response.status} ${response.statusText}`,
      );
    }

    const data = await response.json();
    const divisions = data.divisions || [];

    // Return only divisions that exist in the response
    // The API already filters to only divisions with data
    return divisions
      .map((div: { division: string }) => ({
        division: encodeURIComponent(div.division),
      }));
  } catch (error) {
    console.warn("Failed to fetch divisions for static generation:", error);
    console.warn("Skipping division prefetch – API unavailable during build.");
    // Return only men's divisions as fallback (database only has men's rankings)
    return [
      "Flyweight",
      "Bantamweight",
      "Featherweight",
      "Lightweight",
      "Welterweight",
      "Middleweight",
      "Light Heavyweight",
      "Heavyweight",
    ].map((division) => ({ division }));
  }
}
