"use client";

import { useEffect, useState } from "react";

import type { FighterListItem } from "@/lib/types";
import { useFavoritesStore } from "@/store/favoritesStore";
import { getApiBaseUrl, getFighters } from "@/lib/api";

export function useFighters(initialLimit = 20) {
  const searchTerm = useFavoritesStore((state) => state.searchTerm);
  const stance = useFavoritesStore((state) => state.stanceFilter);
  const [fighters, setFighters] = useState<FighterListItem[]>([]);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadFighters = async (newOffset: number) => {
    let active = true;
    setIsLoading(true);
    setError(null);
    try {
      // If there's a search term or stance filter, use search endpoint
      if (searchTerm || stance) {
        const params = new URLSearchParams();
        if (searchTerm) params.set("q", searchTerm);
        if (stance) params.set("stance", stance);
        const baseUrl = getApiBaseUrl();
        const url = `${baseUrl}/search/?${params.toString()}`;
        const response = await fetch(url, { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`Failed to load fighters (${response.status})`);
        }
        const data: FighterListItem[] = await response.json();
        if (active) {
          setFighters(data);
          setTotal(data.length);
          setHasMore(false); // Search doesn't have pagination yet
          setOffset(0);
        }
      } else {
        // Otherwise use paginated fighters endpoint
        const data = await getFighters(initialLimit, newOffset);
        if (active) {
          setFighters(data.fighters);
          setTotal(data.total);
          setHasMore(data.has_more);
          setOffset(newOffset);
        }
      }
    } catch (err) {
      if (active) {
        setError(err instanceof Error ? err.message : "Unknown error");
        setFighters([]);
      }
    } finally {
      if (active) {
        setIsLoading(false);
      }
    }
  };

  const nextPage = () => loadFighters(offset + initialLimit);
  const prevPage = () => loadFighters(Math.max(0, offset - initialLimit));

  useEffect(() => {
    void loadFighters(0);
  }, [searchTerm, stance]);

  return { fighters, total, offset, hasMore, isLoading, error, nextPage, prevPage };
}
