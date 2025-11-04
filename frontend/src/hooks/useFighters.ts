"use client";

import { useCallback, useMemo } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";

import type { FighterListItem, PaginatedFightersResponse } from "@/lib/types";
import { useFavoritesStore } from "@/store/favoritesStore";
import { getFighters, searchFighters } from "@/lib/api";
import type { ApiError } from "@/lib/errors";

/**
 * Type alias for better readability in TanStack Query generics.
 */
type FightersPage = PaginatedFightersResponse;

/**
 * Flatten all fighters across the paginated response pages.
 */
function flattenPages(pages: PaginatedFightersResponse[] | undefined): FighterListItem[] {
  if (!pages?.length) {
    return [];
  }
  return pages.flatMap((page) => page.fighters);
}

/**
 * React hook that exposes fighter roster data with pagination, filtering, and
 * infinite-scroll support. The hook is backed by TanStack Query so data is
 * cached between navigations and shared across components that request the same
 * filters.
 *
 * @param initialDataOrLimit - Either initial page data from SSG or page size limit
 */
export function useFighters(
  initialDataOrLimit?: PaginatedFightersResponse | number
) {
  const searchTerm = useFavoritesStore((state) => state.searchTerm);
  const stance = useFavoritesStore((state) => state.stanceFilter);
  const division = useFavoritesStore((state) => state.divisionFilter);

  // Support both old API (number) and new API (initialData object)
  const initialData =
    typeof initialDataOrLimit === "object" ? initialDataOrLimit : undefined;
  const pageSize =
    typeof initialDataOrLimit === "number" ? initialDataOrLimit : 20;

  const normalizedSearch = (searchTerm ?? "").trim();
  const isFiltering = Boolean(normalizedSearch || stance || division);

  const queryKey = useMemo(
    () => [
      "fighters",
      {
        search: normalizedSearch,
        stance: stance ?? null,
        division: division ?? null,
        limit: pageSize,
      },
    ],
    [normalizedSearch, stance, division, pageSize]
  );

  const {
    data,
    hasNextPage,
    fetchNextPage,
    isFetchingNextPage,
    refetch,
    isPending,
    error: queryError,
  } = useInfiniteQuery<FightersPage, ApiError>({
    queryKey,
    initialPageParam: 0,
    // Hydrate from SSG data (only when no filters applied)
    initialData:
      initialData && !isFiltering
        ? {
            pages: [initialData],
            pageParams: [0],
          }
        : undefined,
    /**
     * The query function decides between the search endpoint and the general
     * roster endpoint. TanStack Query hands us the offset for the current page.
     */
    queryFn: async ({ pageParam }): Promise<FightersPage> => {
      const offset = typeof pageParam === "number" ? pageParam : 0;
      if (isFiltering) {
        return searchFighters(normalizedSearch, stance, division, pageSize, offset);
      }
      return getFighters(pageSize, offset);
    },
    getNextPageParam: (lastPage: FightersPage) => {
      return lastPage.has_more ? lastPage.offset + lastPage.limit : undefined;
    },
    retry: 2,
  });

  const fighters = useMemo(() => flattenPages(data?.pages), [data]);

  const total = useMemo(() => {
    if (!data?.pages?.length) {
      return 0;
    }
    return data.pages[0]?.total ?? 0;
  }, [data]);

  const latestPage = data?.pages?.[data.pages.length - 1];
  const offset = latestPage?.offset ?? 0;
  const hasMore = Boolean(hasNextPage);

  /**
   * Trigger the next page load when the intersection observer fires. We guard
   * against duplicate requests by checking if a fetch is already in progress
   * or if the backend has no more data to return.
   */
  const loadMore = useCallback(() => {
    if (!hasNextPage || isFetchingNextPage) {
      return;
    }
    void fetchNextPage();
  }, [fetchNextPage, hasNextPage, isFetchingNextPage]);

  /**
   * Allow the UI to retry the most recent request. TanStack Query will reuse
   * cached data and only re-request pages that previously failed.
   */
  const retry = useCallback(() => {
    void refetch();
  }, [refetch]);

  /**
   * During the initial load we show the skeleton grid. Subsequent background
   * refetches keep the list visible while a lightweight loading more indicator
   * handles pagination fetches.
   * Note: When initialData is provided, isPending is false (data available immediately)
   */
  const isLoading = isPending;
  const isLoadingMore = isFetchingNextPage;
  const error = queryError ?? null;

  return {
    fighters,
    total,
    offset,
    hasMore,
    isLoading,
    isLoadingMore,
    error,
    loadMore,
    retry,
    limit: pageSize,
  };
}
