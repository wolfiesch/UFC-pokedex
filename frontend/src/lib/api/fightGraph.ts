import { z } from "zod";

import {
  DEFAULT_CLIENT_API_BASE_URL,
  resolveClientApiBaseUrl,
} from "../api-base-url";
import { ApiError } from "../errors";
import type { FightGraphQueryParams, FightGraphResponse } from "../types";

/**
 * Zod schema describing the structure of a fight graph node. Inline comments
 * explain each constraint so maintainers immediately understand the intent
 * when extending the schema.
 */
const fightGraphNodeSchema = z.object({
  fighter_id: z.string().min(1, "fighter_id is required"),
  name: z.string().min(1, "name is required"),
  division: z.string().nullable().optional(),
  record: z.string().nullable().optional(),
  image_url: z.string().url().or(z.string().length(0)).nullable().optional(),
  total_fights: z.number().int().nonnegative(),
  latest_event_date: z.string().nullable().optional(),
});

/**
 * Schema for a fight result breakdown entry. Each result key is optional but
 * must be a non-negative integer if present, preserving backend semantics.
 */
const fightResultBreakdownSchema = z.record(
  z
    .object({
      win: z.number().int().nonnegative().optional(),
      loss: z.number().int().nonnegative().optional(),
      draw: z.number().int().nonnegative().optional(),
      nc: z.number().int().nonnegative().optional(),
      upcoming: z.number().int().nonnegative().optional(),
      other: z.number().int().nonnegative().optional(),
    })
    .catchall(z.number().int().nonnegative().optional()),
);

/**
 * Schema describing a graph link between two fighters.
 */
const fightGraphLinkSchema = z.object({
  source: z.string().min(1, "source is required"),
  target: z.string().min(1, "target is required"),
  fights: z.number().int().nonnegative(),
  first_event_name: z.string().nullable().optional(),
  first_event_date: z.string().nullable().optional(),
  last_event_name: z.string().nullable().optional(),
  last_event_date: z.string().nullable().optional(),
  result_breakdown: fightResultBreakdownSchema,
});

/**
 * Complete schema for the FightWeb graph response.
 */
const fightGraphResponseSchema = z.object({
  nodes: z.array(fightGraphNodeSchema),
  links: z.array(fightGraphLinkSchema),
  metadata: z.record(z.unknown()).default({}),
});

/**
 * Validate and normalise query parameters before constructing the request URL.
 * Numeric filters default to null when parsing fails to avoid sending invalid
 * values to the API.
 */
function prepareQueryParams(
  params: FightGraphQueryParams,
): Record<string, string | number | boolean> {
  const query: Record<string, string | number | boolean> = {};

  if (params.division && params.division.trim().length > 0) {
    query.division = params.division.trim();
  }

  if (
    typeof params.startYear === "number" &&
    Number.isFinite(params.startYear)
  ) {
    query.start_year = params.startYear;
  }

  if (typeof params.endYear === "number" && Number.isFinite(params.endYear)) {
    query.end_year = params.endYear;
  }

  if (typeof params.limit === "number" && Number.isFinite(params.limit)) {
    query.limit = params.limit;
  }

  if (typeof params.includeUpcoming === "boolean") {
    query.include_upcoming = params.includeUpcoming;
  }

  return query;
}

/**
 * Convert a query object into a serialized query string. Keys with undefined
 * values are skipped. This helper keeps the fetch logic focused on HTTP
 * concerns rather than string manipulation.
 */
function toQueryString(
  query: Record<string, string | number | boolean>,
): string {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(query)) {
    if (typeof value === "boolean") {
      searchParams.set(key, value ? "true" : "false");
    } else {
      searchParams.set(key, String(value));
    }
  }

  const serialized = searchParams.toString();
  return serialized.length > 0 ? `?${serialized}` : "";
}

/**
 * Resolve the client-side API base URL, mirroring the logic used by the rest
 * of the application. A descriptive ApiError is thrown when URL resolution
 * fails so calling code can surface an actionable message.
 */
function resolveBaseUrl(): string {
  try {
    return resolveClientApiBaseUrl(
      process.env.NEXT_PUBLIC_API_BASE_URL,
      DEFAULT_CLIENT_API_BASE_URL,
    );
  } catch (error) {
    throw new ApiError("Invalid API base URL", {
      statusCode: 500,
      detail:
        error instanceof Error ? error.message : "Unable to resolve base URL",
      context: "fightGraphClient",
    });
  }
}

/**
 * Fetch FightWeb graph data with runtime validation. Consumers receive a
 * strongly typed payload or an ApiError describing the failure mode.
 */
export async function fetchFightGraph(
  params: FightGraphQueryParams,
): Promise<FightGraphResponse> {
  const queryString = toQueryString(prepareQueryParams(params));
  const baseUrl = resolveBaseUrl();
  const endpoint = `${baseUrl}/fightweb/graph${queryString}`;

  let response: Response;

  try {
    response = await fetch(endpoint, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      cache: "no-store",
    });
  } catch (error) {
    throw new ApiError("Failed to reach the FightWeb service", {
      statusCode: 503,
      detail: error instanceof Error ? error.message : undefined,
      context: "fightGraphClient",
    });
  }

  if (!response.ok) {
    const detail = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new ApiError("Fight graph request failed", {
      statusCode: response.status,
      detail: typeof detail?.detail === "string" ? detail.detail : undefined,
      context: "fightGraphClient",
    });
  }

  const json = await response.json();
  const parsed = fightGraphResponseSchema.safeParse(json);

  if (!parsed.success) {
    throw new ApiError("Fight graph response validation failed", {
      statusCode: 500,
      detail: parsed.error.message,
      context: "fightGraphClient",
    });
  }

  return parsed.data;
}
