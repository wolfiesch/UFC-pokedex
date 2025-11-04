"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { FighterListItem } from "@/lib/types";
import { useFavoritesStore } from "@/store/favoritesStore";
import { getFighters, searchFighters } from "@/lib/api";
import { ApiError } from "@/lib/errors";

export function useFighters(initialLimit = 20) {
  const searchTerm = useFavoritesStore((state) => state.searchTerm);
  const stance = useFavoritesStore((state) => state.stanceFilter);
  const division = useFavoritesStore((state) => state.divisionFilter);
  const [fighters, setFighters] = useState<FighterListItem[]>([]);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const pageSize = initialLimit;

  // Store last request params for retry
  const lastRequestRef = useRef<{ offset: number; append: boolean } | null>(null);
  const requestVersionRef = useRef(0);

  const loadFighters = useCallback(async (newOffset: number, append = false) => {
    // Store request params for potential retry
    lastRequestRef.current = { offset: newOffset, append };

    const requestVersion = append
      ? requestVersionRef.current
      : requestVersionRef.current + 1;
    if (!append) {
      requestVersionRef.current = requestVersion;
    }

    if (append) {
      setIsLoadingMore(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const trimmedSearch = (searchTerm ?? "").trim();
      const isFiltering = Boolean(trimmedSearch || stance || division);

      let data;
      if (isFiltering) {
        data = await searchFighters(trimmedSearch, stance, division, pageSize, newOffset);
      } else {
        data = await getFighters(pageSize, newOffset);
      }

      if (requestVersion !== requestVersionRef.current) {
        return;
      }

      if (append) {
        setFighters((prev) => [...prev, ...data.fighters]);
      } else {
        setFighters(data.fighters);
      }
      setTotal(data.total);
      setHasMore(data.has_more);
      setOffset(data.offset);
    } catch (err) {
      if (requestVersion !== requestVersionRef.current) {
        return;
      }

      const apiError = err instanceof ApiError
        ? err
        : new ApiError(
            err instanceof Error ? err.message : "Unknown error occurred",
            { statusCode: 0 }
          );

      setError(apiError);

      if (!append) {
        setFighters([]);
      }
    } finally {
      if (requestVersion !== requestVersionRef.current) {
        return;
      }

      if (append) {
        setIsLoadingMore(false);
      } else {
        setIsLoading(false);
      }
    }
  }, [searchTerm, stance, division, pageSize]);

  const loadMore = useCallback(() => {
    if (!hasMore || isLoadingMore || isLoading) return;
    void loadFighters(offset + pageSize, true);
  }, [hasMore, isLoadingMore, isLoading, offset, pageSize, loadFighters]);

  /**
   * Retry the last failed request
   */
  const retry = useCallback(() => {
    if (lastRequestRef.current) {
      const { offset: retryOffset, append } = lastRequestRef.current;
      void loadFighters(retryOffset, append);
    } else {
      // No previous request, start fresh
      void loadFighters(0, false);
    }
  }, [loadFighters]);

  useEffect(() => {
    setOffset(0);
    setFighters([]);
    void loadFighters(0, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchTerm, stance, division]);

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
