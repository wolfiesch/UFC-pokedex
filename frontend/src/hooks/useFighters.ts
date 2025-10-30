"use client";

import { useEffect, useState } from "react";

import type { FighterListItem } from "@/lib/types";
import { useFavoritesStore } from "@/store/favoritesStore";
import { getApiBaseUrl } from "@/lib/api";

export function useFighters() {
  const searchTerm = useFavoritesStore((state) => state.searchTerm);
  const stance = useFavoritesStore((state) => state.stanceFilter);
  const [fighters, setFighters] = useState<FighterListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (searchTerm) params.set("q", searchTerm);
        if (stance) params.set("stance", stance);
        const baseUrl = getApiBaseUrl();
        const url =
          params.size > 0 ? `${baseUrl}/search?${params.toString()}` : `${baseUrl}/fighters/`;
        const response = await fetch(url, { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`Failed to load fighters (${response.status})`);
        }
        const data: FighterListItem[] = await response.json();
        if (active) {
          setFighters(data);
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
    }
    void load();
    return () => {
      active = false;
    };
  }, [searchTerm, stance]);

  return { fighters, isLoading, error };
}
