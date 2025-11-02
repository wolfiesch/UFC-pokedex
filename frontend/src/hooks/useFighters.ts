"use client";

import { useEffect, useState } from "react";

import type { FighterListItem } from "@/lib/types";
import { useFavoritesStore } from "@/store/favoritesStore";
import { getFighters, searchFighters } from "@/lib/api";

export function useFighters(initialLimit = 20) {
  const searchTerm = useFavoritesStore((state) => state.searchTerm);
  const stance = useFavoritesStore((state) => state.stanceFilter);
  const [fighters, setFighters] = useState<FighterListItem[]>([]);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pageSize = initialLimit;

  const loadFighters = async (newOffset: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const trimmedSearch = (searchTerm ?? "").trim();
      const isFiltering = Boolean(trimmedSearch || stance);

      if (isFiltering) {
        const data = await searchFighters(trimmedSearch, stance, pageSize, newOffset);
        setFighters(data.fighters);
        setTotal(data.total);
        setHasMore(data.has_more);
        setOffset(data.offset);
      } else {
        const data = await getFighters(pageSize, newOffset);
        setFighters(data.fighters);
        setTotal(data.total);
        setHasMore(data.has_more);
        setOffset(data.offset);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setFighters([]);
    } finally {
      setIsLoading(false);
    }
  };

  const nextPage = () => loadFighters(offset + pageSize);
  const prevPage = () => loadFighters(Math.max(0, offset - pageSize));

  useEffect(() => {
    setOffset(0);
    void loadFighters(0);
  }, [searchTerm, stance, pageSize]);

  return {
    fighters,
    total,
    offset,
    hasMore,
    isLoading,
    error,
    nextPage,
    prevPage,
    limit: pageSize,
  };
}
