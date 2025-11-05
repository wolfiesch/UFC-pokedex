"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import type { FighterListItem, PaginatedFightersResponse } from "@/lib/types";
import { useFavoritesStore } from "@/store/favoritesStore";
import { getFighters, searchFighters } from "@/lib/api";
import type { ApiError } from "@/lib/errors";

const DEFAULT_LIMIT = 20;
const MIN_LIMIT = 12;
const MAX_LIMIT = 60;

function parseInteger(raw: string | null): number | null {
  if (raw === null || raw.trim().length === 0) {
    return null;
  }
  const parsed = Number.parseInt(raw, 10);
  return Number.isNaN(parsed) ? null : parsed;
}

function clampLimit(value: number | null, fallback: number): number {
  if (value === null || !Number.isFinite(value)) {
    return fallback;
  }
  const truncated = Math.trunc(value);
  if (Number.isNaN(truncated) || truncated <= 0) {
    return fallback;
  }
  return Math.min(Math.max(truncated, MIN_LIMIT), MAX_LIMIT);
}

function normaliseOffset(value: number | null, limit: number): number {
  if (value === null || !Number.isFinite(value)) {
    return 0;
  }
  const truncated = Math.trunc(value);
  if (Number.isNaN(truncated) || truncated <= 0) {
    return 0;
  }
  const snapped = Math.floor(truncated / Math.max(1, limit)) * Math.max(1, limit);
  return Math.max(0, snapped);
}

/**
 * React hook that exposes fighter roster data with pagination, filtering, and
 * limit/offset coordination tied to the URL query string.
 *
 * @param initialDataOrLimit - Either initial page data from SSG or page size limit
 */
export function useFighters(
  initialDataOrLimit?: PaginatedFightersResponse | number,
) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const searchTerm = useFavoritesStore((state) => state.searchTerm);
  const stance = useFavoritesStore((state) => state.stanceFilter);
  const division = useFavoritesStore((state) => state.divisionFilter);

  const initialData =
    typeof initialDataOrLimit === "object" ? initialDataOrLimit : undefined;
  const fallbackLimit =
    typeof initialDataOrLimit === "number" ? initialDataOrLimit : DEFAULT_LIMIT;

  const limitParam = parseInteger(searchParams?.get("limit") ?? null);
  const offsetParam = parseInteger(searchParams?.get("offset") ?? null);

  const limit = clampLimit(limitParam, initialData?.limit ?? fallbackLimit);
  const offset = normaliseOffset(
    offsetParam ?? initialData?.offset ?? 0,
    limit,
  );

  const updateQueryParams = useCallback(
    (updates: Partial<{ limit: number; offset: number }> | null) => {
      const current = new URLSearchParams(searchParams?.toString() ?? "");
      if (updates?.limit !== undefined) {
        if (updates.limit === DEFAULT_LIMIT) {
          current.delete("limit");
        } else {
          current.set("limit", String(updates.limit));
        }
      }
      if (updates?.offset !== undefined) {
        if (updates.offset === 0) {
          current.delete("offset");
        } else {
          current.set("offset", String(updates.offset));
        }
      }
      const nextQuery = current.toString();
      const target = nextQuery ? `${pathname}?${nextQuery}` : pathname;
      router.replace(target, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const setOffset = useCallback(
    (nextOffset: number) => {
      const safeOffset = normaliseOffset(nextOffset, limit);
      if (safeOffset === offset) {
        return;
      }
      updateQueryParams({ offset: safeOffset });
    },
    [limit, offset, updateQueryParams],
  );

  const setLimit = useCallback(
    (nextLimit: number) => {
      const safeLimit = clampLimit(nextLimit, limit);
      if (safeLimit === limit) {
        return;
      }
      updateQueryParams({ limit: safeLimit, offset: 0 });
    },
    [limit, updateQueryParams],
  );

  const normalizedSearch = (searchTerm ?? "").trim();
  const isFiltering = Boolean(normalizedSearch || stance || division);

  const queryKey = useMemo(
    () => [
      "fighters",
      {
        search: normalizedSearch,
        stance: stance ?? null,
        division: division ?? null,
        limit,
        offset,
      },
    ],
    [normalizedSearch, stance, division, limit, offset],
  );

  const queryFn = useCallback(async (): Promise<PaginatedFightersResponse> => {
    if (isFiltering) {
      return searchFighters(normalizedSearch, stance, division, limit, offset);
    }
    return getFighters(limit, offset);
  }, [isFiltering, normalizedSearch, stance, division, limit, offset]);

  const initialQueryData =
    !isFiltering &&
    initialData &&
    initialData.limit === limit &&
    initialData.offset === offset
      ? initialData
      : undefined;

  const {
    data,
    isPending,
    isFetching,
    error: queryError,
    refetch,
  } = useQuery<PaginatedFightersResponse, ApiError>({
    queryKey,
    queryFn,
    initialData: initialQueryData,
    keepPreviousData: true,
    staleTime: 30_000,
  });

  const fighters: FighterListItem[] = data?.fighters ?? [];
  const total = data?.total ?? 0;
  const hasMore = offset + limit < total;
  const canPreviousPage = offset > 0;
  const currentPage = Math.max(1, Math.floor(offset / Math.max(1, limit)) + 1);
  const totalPages = Math.max(1, Math.ceil(total / Math.max(1, limit)));

  const goToNextPage = useCallback(() => {
    if (!hasMore) {
      return;
    }
    setOffset(offset + limit);
  }, [hasMore, offset, limit, setOffset]);

  const goToPreviousPage = useCallback(() => {
    if (!canPreviousPage) {
      return;
    }
    setOffset(Math.max(0, offset - limit));
  }, [canPreviousPage, offset, limit, setOffset]);

  const resetPagination = useCallback(() => {
    if (offset !== 0) {
      setOffset(0);
    }
  }, [offset, setOffset]);

  const filtersRef = useRef({
    search: normalizedSearch,
    stance: stance ?? null,
    division: division ?? null,
  });

  useEffect(() => {
    const prev = filtersRef.current;
    const next = {
      search: normalizedSearch,
      stance: stance ?? null,
      division: division ?? null,
    };
    const hasChanged =
      prev.search !== next.search ||
      prev.stance !== next.stance ||
      prev.division !== next.division;
    if (hasChanged) {
      filtersRef.current = next;
      if (offset !== 0) {
        setOffset(0);
      }
    }
  }, [normalizedSearch, stance, division, offset, setOffset]);

  const isLoading = isPending && !data;
  const isFetchingPage = isFetching && !isPending;
  const error = queryError ?? null;

  const retry = useCallback(() => {
    void refetch();
  }, [refetch]);

  return {
    fighters,
    total,
    limit,
    offset,
    pageCount: totalPages,
    currentPage,
    canNextPage: hasMore,
    canPreviousPage,
    isLoading,
    isFetchingPage,
    error,
    goToNextPage,
    goToPreviousPage,
    setLimit,
    setOffset,
    resetPagination,
    retry,
  };
}
