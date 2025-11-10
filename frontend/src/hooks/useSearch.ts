"use client";

import { useMemo } from "react";

import { useFavoritesFiltersStore } from "@/store/favoritesFiltersStore";

export function useSearch() {
  const searchTerm = useFavoritesFiltersStore((state) => state.searchTerm);
  const stanceFilter = useFavoritesFiltersStore((state) => state.stanceFilter);
  const divisionFilter = useFavoritesFiltersStore((state) => state.divisionFilter);
  const championStatusFilters = useFavoritesFiltersStore((state) => state.championStatusFilters);
  const winStreakCount = useFavoritesFiltersStore((state) => state.winStreakCount);
  const lossStreakCount = useFavoritesFiltersStore((state) => state.lossStreakCount);
  const setSearchTerm = useFavoritesFiltersStore((state) => state.setSearchTerm);
  const setStanceFilter = useFavoritesFiltersStore((state) => state.setStanceFilter);
  const setDivisionFilter = useFavoritesFiltersStore((state) => state.setDivisionFilter);
  const toggleChampionStatusFilter = useFavoritesFiltersStore((state) => state.toggleChampionStatusFilter);
  const setWinStreakCount = useFavoritesFiltersStore((state) => state.setWinStreakCount);
  const setLossStreakCount = useFavoritesFiltersStore((state) => state.setLossStreakCount);

  return useMemo(
    () => ({
      searchTerm,
      stanceFilter,
      divisionFilter,
      championStatusFilters,
      winStreakCount,
      lossStreakCount,
      setSearchTerm,
      setStanceFilter,
      setDivisionFilter,
      toggleChampionStatusFilter,
      setWinStreakCount,
      setLossStreakCount,
    }),
    [
      searchTerm,
      stanceFilter,
      divisionFilter,
      championStatusFilters,
      winStreakCount,
      lossStreakCount,
      setSearchTerm,
      setStanceFilter,
      setDivisionFilter,
      toggleChampionStatusFilter,
      setWinStreakCount,
      setLossStreakCount,
    ],
  );
}
