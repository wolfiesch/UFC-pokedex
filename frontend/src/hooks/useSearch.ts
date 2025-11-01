"use client";

import { useFavoritesStore } from "@/store/favoritesStore";

export function useSearch() {
  const searchTerm = useFavoritesStore((state) => state.searchTerm);
  const stanceFilter = useFavoritesStore((state) => state.stanceFilter);
  const setSearchTerm = useFavoritesStore((state) => state.setSearchTerm);
  const setStanceFilter = useFavoritesStore((state) => state.setStanceFilter);

  return { searchTerm, stanceFilter, setSearchTerm, setStanceFilter };
}
