"use client";

import { useFavoritesStore } from "@/store/favoritesStore";

/**
 * Hook for accessing favorites functionality
 * Provides backward compatibility with the old localStorage-based API
 * while using the new backend-connected store
 */
export function useFavorites() {
  const store = useFavoritesStore();

  // Auto-initialize on first use
  if (typeof window !== "undefined" && !store.isInitialized && !store.isLoading) {
    store.initialize();
  }

  // Return backward-compatible API
  return {
    favorites: store.getFavorites(), // Get favorites array
    toggleFavorite: store.toggleFavorite, // Async toggle function
    isFavorite: store.isFavorite, // Helper to check if favorited
    isLoading: store.isLoading,
    error: store.error,

    // Filter state (for favorites page)
    searchTerm: store.searchTerm,
    stanceFilter: store.stanceFilter,
    divisionFilter: store.divisionFilter,
    championStatusFilters: store.championStatusFilters,
    setSearchTerm: store.setSearchTerm,
    setStanceFilter: store.setStanceFilter,
    setDivisionFilter: store.setDivisionFilter,
    toggleChampionStatusFilter: store.toggleChampionStatusFilter,
  };
}
