"use client";

import { useMemo } from "react";

import { useFavoritesFiltersStore } from "@/store/favoritesFiltersStore";

export function useSearch() {
  const searchTerm = useFavoritesFiltersStore((state) => state.searchTerm);
  const stanceFilter = useFavoritesFiltersStore((state) => state.stanceFilter);
  const divisionFilter = useFavoritesFiltersStore(
    (state) => state.divisionFilter,
  );
  const nationalityFilter = useFavoritesFiltersStore(
    (state) => state.nationalityFilter,
  );
  const championStatusFilters = useFavoritesFiltersStore(
    (state) => state.championStatusFilters,
  );
  const winStreakCount = useFavoritesFiltersStore(
    (state) => state.winStreakCount,
  );
  const lossStreakCount = useFavoritesFiltersStore(
    (state) => state.lossStreakCount,
  );
  const setSearchTerm = useFavoritesFiltersStore(
    (state) => state.setSearchTerm,
  );
  const setStanceFilter = useFavoritesFiltersStore(
    (state) => state.setStanceFilter,
  );
  const setDivisionFilter = useFavoritesFiltersStore(
    (state) => state.setDivisionFilter,
  );
  const setNationalityFilter = useFavoritesFiltersStore(
    (state) => state.setNationalityFilter,
  );
  const toggleChampionStatusFilter = useFavoritesFiltersStore(
    (state) => state.toggleChampionStatusFilter,
  );
  const setWinStreakCount = useFavoritesFiltersStore(
    (state) => state.setWinStreakCount,
  );
  const setLossStreakCount = useFavoritesFiltersStore(
    (state) => state.setLossStreakCount,
  );

  return useMemo(
    () => ({
      searchTerm,
      stanceFilter,
      divisionFilter,
      nationalityFilter,
      championStatusFilters,
      winStreakCount,
      lossStreakCount,
      setSearchTerm,
      setStanceFilter,
      setDivisionFilter,
      setNationalityFilter,
      toggleChampionStatusFilter,
      setWinStreakCount,
      setLossStreakCount,
    }),
    [
      searchTerm,
      stanceFilter,
      divisionFilter,
      nationalityFilter,
      championStatusFilters,
      winStreakCount,
      lossStreakCount,
      setSearchTerm,
      setStanceFilter,
      setDivisionFilter,
      setNationalityFilter,
      toggleChampionStatusFilter,
      setWinStreakCount,
      setLossStreakCount,
    ],
  );
}
