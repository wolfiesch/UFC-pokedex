import type {
  FightGraphQueryParams,
  FightWebSortOption,
} from "@/lib/types";

import { DEFAULT_SORT, isValidFightWebSortOption } from "./sort-utils";

export const MIN_LIMIT = 25;
export const MAX_LIMIT = 400;

export function clampLimit(
  value: number | null | undefined,
  fallback = 150,
): number {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return fallback;
  }
  return Math.min(MAX_LIMIT, Math.max(MIN_LIMIT, Math.round(value)));
}

export function sanitizeYear(value: number | null | undefined): number | null {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return null;
  }
  return value;
}

export function normalizeFilters(
  filters: FightGraphQueryParams,
  fallbackLimit = 150,
): FightGraphQueryParams {
  const limit = clampLimit(filters.limit, fallbackLimit);
  let startYear = sanitizeYear(filters.startYear);
  let endYear = sanitizeYear(filters.endYear);
  if (startYear !== null && endYear !== null && startYear > endYear) {
    [startYear, endYear] = [endYear, startYear];
  }
  const sortBy = resolveSortOption(filters.sortBy);
  return {
    division: filters.division ?? null,
    startYear,
    endYear,
    limit,
    includeUpcoming: Boolean(filters.includeUpcoming),
    sortBy,
  };
}

export function filtersEqual(
  a: FightGraphQueryParams,
  b: FightGraphQueryParams,
): boolean {
  return (
    (a.division ?? null) === (b.division ?? null) &&
    (a.startYear ?? null) === (b.startYear ?? null) &&
    (a.endYear ?? null) === (b.endYear ?? null) &&
    clampLimit(a.limit ?? null) === clampLimit(b.limit ?? null) &&
    Boolean(a.includeUpcoming) === Boolean(b.includeUpcoming) &&
    resolveSortOption(a.sortBy) === resolveSortOption(b.sortBy)
  );
}

function resolveSortOption(
  value: FightWebSortOption | string | null | undefined,
): FightWebSortOption {
  if (value && isValidFightWebSortOption(value)) {
    return value;
  }
  return DEFAULT_SORT;
}
