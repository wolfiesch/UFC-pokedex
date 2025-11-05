"use client";

import { useMemo } from "react";

import { useFavoritesStore } from "@/store/favoritesStore";

export function useSearch() {
  const searchTerm = useFavoritesStore((state) => state.searchTerm);
  const stanceFilter = useFavoritesStore((state) => state.stanceFilter);
  const divisionFilter = useFavoritesStore((state) => state.divisionFilter);
  const championStatusFilters = useFavoritesStore((state) => state.championStatusFilters);
  const winStreakCount = useFavoritesStore((state) => state.winStreakCount);
  const lossStreakCount = useFavoritesStore((state) => state.lossStreakCount);
  const setSearchTerm = useFavoritesStore((state) => state.setSearchTerm);
  const setStanceFilter = useFavoritesStore((state) => state.setStanceFilter);
  const setDivisionFilter = useFavoritesStore((state) => state.setDivisionFilter);
  const toggleChampionStatusFilter = useFavoritesStore((state) => state.toggleChampionStatusFilter);
  const setWinStreakCount = useFavoritesStore((state) => state.setWinStreakCount);
  const setLossStreakCount = useFavoritesStore((state) => state.setLossStreakCount);

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
