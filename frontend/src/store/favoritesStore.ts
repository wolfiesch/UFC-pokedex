"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { FighterListItem } from "@/lib/types";

type FavoritesState = {
  favorites: FighterListItem[];
  searchTerm: string;
  stanceFilter: string | null;
  divisionFilter: string | null;
  championStatusFilters: string[];
  toggleFavorite: (fighter: FighterListItem) => void;
  setSearchTerm: (term: string) => void;
  setStanceFilter: (stance: string | null) => void;
  setDivisionFilter: (division: string | null) => void;
  toggleChampionStatusFilter: (status: string) => void;
};

export const useFavoritesStore = create<FavoritesState>()(
  persist(
    (set, get) => ({
      favorites: [],
      searchTerm: "",
      stanceFilter: null,
      divisionFilter: null,
      championStatusFilters: [],
      toggleFavorite: (fighter) => {
        const favorites = get().favorites;
        const exists = favorites.some((fav) => fav.fighter_id === fighter.fighter_id);
        set({
          favorites: exists
            ? favorites.filter((fav) => fav.fighter_id !== fighter.fighter_id)
            : [...favorites, fighter],
        });
      },
      setSearchTerm: (term) => set({ searchTerm: term }),
      setStanceFilter: (stance) => set({ stanceFilter: stance }),
      setDivisionFilter: (division) => set({ divisionFilter: division }),
      toggleChampionStatusFilter: (status) => {
        const filters = get().championStatusFilters;
        const exists = filters.includes(status);
        set({
          championStatusFilters: exists
            ? filters.filter((f) => f !== status)
            : [...filters, status],
        });
      },
    }),
    {
      name: "ufc-pokedex-favorites",
      partialize: (state) => ({
        favorites: state.favorites,
        searchTerm: state.searchTerm,
        stanceFilter: state.stanceFilter,
        divisionFilter: state.divisionFilter,
        championStatusFilters: state.championStatusFilters,
      }),
    },
  ),
);
