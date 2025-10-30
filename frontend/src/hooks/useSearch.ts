"use client";

import { useMemo } from "react";

import { useFavoritesStore } from "@/store/favoritesStore";

export function useSearch() {
  const searchTerm = useFavoritesStore((state) => state.searchTerm);
  const stanceFilter = useFavoritesStore((state) => state.stanceFilter);
  const setSearchTerm = useFavoritesStore((state) => state.setSearchTerm);
  const setStanceFilter = useFavoritesStore((state) => state.setStanceFilter);

  return useMemo(
    () => ({ searchTerm, stanceFilter, setSearchTerm, setStanceFilter }),
    [searchTerm, stanceFilter, setSearchTerm, setStanceFilter],
  );
}
