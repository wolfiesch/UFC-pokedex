import type { FightGraphQueryParams } from "@/lib/types";

export const MIN_LIMIT = 25;
export const MAX_LIMIT = 400;

export function clampLimit(
  value: number | null | undefined,
  fallback = 150
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
  fallbackLimit = 150
): FightGraphQueryParams {
  const limit = clampLimit(filters.limit, fallbackLimit);
  let startYear = sanitizeYear(filters.startYear);
  let endYear = sanitizeYear(filters.endYear);
  if (startYear !== null && endYear !== null && startYear > endYear) {
    [startYear, endYear] = [endYear, startYear];
  }
  return {
    division: filters.division ?? null,
    startYear,
    endYear,
    limit,
    includeUpcoming: Boolean(filters.includeUpcoming),
  };
}
