"use client";

import { useFavoritesStore } from "@/store/favoritesStore";

export function useFavorites() {
  const favorites = useFavoritesStore((state) => state.favorites);
  const toggleFavorite = useFavoritesStore((state) => state.toggleFavorite);

  return { favorites, toggleFavorite };
}
