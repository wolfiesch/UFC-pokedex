"use client";

import { useMemo } from "react";

import { useFavoritesStore } from "@/store/favoritesStore";

export function useSearch() {
  const searchTerm = useFavoritesStore((state) => state.searchTerm);
  const stanceFilter = useFavoritesStore((state) => state.stanceFilter);
  const divisionFilter = useFavoritesStore((state) => state.divisionFilter);
  const championStatusFilters = useFavoritesStore((state) => state.championStatusFilters);
  const setSearchTerm = useFavoritesStore((state) => state.setSearchTerm);
  const setStanceFilter = useFavoritesStore((state) => state.setStanceFilter);
  const setDivisionFilter = useFavoritesStore((state) => state.setDivisionFilter);
  const toggleChampionStatusFilter = useFavoritesStore((state) => state.toggleChampionStatusFilter);

  return useMemo(
    () => ({
      searchTerm,
      stanceFilter,
      divisionFilter,
      championStatusFilters,
      setSearchTerm,
      setStanceFilter,
      setDivisionFilter,
      toggleChampionStatusFilter,
    }),
    [
      searchTerm,
      stanceFilter,
      divisionFilter,
      championStatusFilters,
      setSearchTerm,
      setStanceFilter,
      setDivisionFilter,
      toggleChampionStatusFilter,
    ],
  );
}
