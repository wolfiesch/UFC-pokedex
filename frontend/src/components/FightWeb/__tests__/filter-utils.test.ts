import { describe, expect, it } from "vitest";

import type { FightGraphQueryParams } from "@/lib/types";

import {
  clampLimit,
  normalizeFilters,
  MIN_LIMIT,
  MAX_LIMIT,
} from "../filter-utils";

describe("filter-utils", () => {
  it("clamps limits within bounds", () => {
    expect(clampLimit(10)).toBe(MIN_LIMIT);
    expect(clampLimit(999)).toBe(MAX_LIMIT);
    expect(clampLimit(120)).toBe(120);
    expect(clampLimit(null, 180)).toBe(180);
  });

  it("normalizes start and end years", () => {
    const filters: FightGraphQueryParams = {
      division: "Featherweight",
      startYear: 2025,
      endYear: 2020,
      limit: 500,
      includeUpcoming: true,
    };

    const normalised = normalizeFilters(filters);
    expect(normalised.startYear).toBe(2020);
    expect(normalised.endYear).toBe(2025);
    expect(normalised.limit).toBe(MAX_LIMIT);
    expect(normalised.includeUpcoming).toBe(true);
  });

  it("ensures booleans are coerced", () => {
    const filters: FightGraphQueryParams = {
      division: null,
      startYear: null,
      endYear: null,
      limit: 140,
      includeUpcoming: undefined,
    };

    const normalised = normalizeFilters(filters);
    expect(normalised.includeUpcoming).toBe(false);
  });
});
