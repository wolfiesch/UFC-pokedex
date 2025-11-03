"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { FighterListItem } from "@/lib/types";

type FavoritesState = {
  favorites: FighterListItem[];
  searchTerm: string;
  stanceFilter: string | null;
  divisionFilter: string | null;
  toggleFavorite: (fighter: FighterListItem) => void;
  setSearchTerm: (term: string) => void;
  setStanceFilter: (stance: string | null) => void;
  setDivisionFilter: (division: string | null) => void;
};

export const useFavoritesStore = create<FavoritesState>()(
  persist(
    (set, get) => ({
      favorites: [],
      searchTerm: "",
      stanceFilter: null,
      divisionFilter: null,
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
    }),
    {
      name: "ufc-pokedex-favorites",
      partialize: (state) => ({
        favorites: state.favorites,
        searchTerm: state.searchTerm,
        stanceFilter: state.stanceFilter,
        divisionFilter: state.divisionFilter,
      }),
    },
  ),
);
