"use client";

import { useEffect } from "react";

import { useFavoritesStore } from "@/store/favoritesStore";

type UseFavoritesOptions = {
  /**
   * Automatically hydrate favorites from the backend when the hook mounts.
   * Defaults to false so the home page can render without incurring the
   * favorites API requests during the critical first paint.
   */
  autoInitialize?: boolean;
};

/**
 * Hook for accessing favorites functionality
 * Provides backward compatibility with the old localStorage-based API
 * while using the new backend-connected store
 */
export function useFavorites(options?: UseFavoritesOptions) {
  const {
    initialize,
    isInitialized,
    isLoading,
    getFavorites,
    toggleFavorite,
    isFavorite,
    error,
    searchTerm,
    stanceFilter,
    divisionFilter,
    championStatusFilters,
    setSearchTerm,
    setStanceFilter,
    setDivisionFilter,
    toggleChampionStatusFilter,
  } = useFavoritesStore();
  const autoInitialize = options?.autoInitialize ?? false;

  useEffect(() => {
    if (!autoInitialize) {
      return;
    }

    if (!isInitialized && !isLoading) {
      void initialize();
    }
  }, [autoInitialize, initialize, isInitialized, isLoading]);

  // Return backward-compatible API
  return {
    favorites: getFavorites(), // Get favorites array
    toggleFavorite, // Async toggle function
    isFavorite, // Helper to check if favorited
    isLoading,
    error,

    // Filter state (for favorites page)
    searchTerm,
    stanceFilter,
    divisionFilter,
    championStatusFilters,
    setSearchTerm,
    setStanceFilter,
    setDivisionFilter,
    toggleChampionStatusFilter,
  };
}
