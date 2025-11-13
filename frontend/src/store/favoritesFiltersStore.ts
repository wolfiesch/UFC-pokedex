"use client";

import { createWithEqualityFn } from "zustand/traditional";

type FavoritesFiltersState = {
  searchTerm: string;
  stanceFilter: string | null;
  divisionFilter: string | null;
  nationalityFilter: string | null;
  championStatusFilters: string[];
  winStreakCount: number | null;
  lossStreakCount: number | null;
  setSearchTerm: (term: string) => void;
  setStanceFilter: (stance: string | null) => void;
  setDivisionFilter: (division: string | null) => void;
  setNationalityFilter: (nationality: string | null) => void;
  toggleChampionStatusFilter: (status: string) => void;
  setWinStreakCount: (count: number | null) => void;
  setLossStreakCount: (count: number | null) => void;
  clearStreakFilters: () => void;
  resetFilters: () => void;
};

const defaultFilters = {
  searchTerm: "",
  stanceFilter: null,
  divisionFilter: null,
  nationalityFilter: null,
  championStatusFilters: [] as string[],
  winStreakCount: null as number | null,
  lossStreakCount: null as number | null,
};

export const useFavoritesFiltersStore = createWithEqualityFn<FavoritesFiltersState>((set, get) => ({
  ...defaultFilters,
  setSearchTerm: (term) => set({ searchTerm: term }),
  setStanceFilter: (stance) => set({ stanceFilter: stance }),
  setDivisionFilter: (division) => set({ divisionFilter: division }),
  setNationalityFilter: (nationality) => set({ nationalityFilter: nationality }),
  toggleChampionStatusFilter: (status) =>
    set((state) => {
      const exists = state.championStatusFilters.includes(status);
      return {
        championStatusFilters: exists
          ? state.championStatusFilters.filter((entry) => entry !== status)
          : [...state.championStatusFilters, status],
      };
    }),
  setWinStreakCount: (count) =>
    set({
      winStreakCount: count,
      lossStreakCount: count !== null ? null : get().lossStreakCount,
    }),
  setLossStreakCount: (count) =>
    set({
      lossStreakCount: count,
      winStreakCount: count !== null ? null : get().winStreakCount,
    }),
  clearStreakFilters: () => set({ winStreakCount: null, lossStreakCount: null }),
  resetFilters: () => set({ ...defaultFilters }),
}));
