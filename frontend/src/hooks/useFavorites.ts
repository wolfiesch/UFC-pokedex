"use client";

import { useEffect } from "react";
import { shallow } from "zustand/shallow";

import { useFavoritesStore } from "@/store/favoritesStore";
import { useFavoritesFiltersStore } from "@/store/favoritesFiltersStore";

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
  const favorites = useFavoritesStore((state) => state.favoriteListCache);
  const toggleFavorite = useFavoritesStore((state) => state.toggleFavorite);
  const isFavorite = useFavoritesStore((state) => state.isFavorite);
  const { initialize, isInitialized, isLoading, error } = useFavoritesStore(
    (state) => ({
      initialize: state.initialize,
      isInitialized: state.isInitialized,
      isLoading: state.isLoading,
      error: state.error,
    }),
    shallow,
  );
  const {
    searchTerm,
    stanceFilter,
    divisionFilter,
    championStatusFilters,
    setSearchTerm,
    setStanceFilter,
    setDivisionFilter,
    toggleChampionStatusFilter,
  } = useFavoritesFiltersStore(
    (state) => ({
      searchTerm: state.searchTerm,
      stanceFilter: state.stanceFilter,
      divisionFilter: state.divisionFilter,
      championStatusFilters: state.championStatusFilters,
      setSearchTerm: state.setSearchTerm,
      setStanceFilter: state.setStanceFilter,
      setDivisionFilter: state.setDivisionFilter,
      toggleChampionStatusFilter: state.toggleChampionStatusFilter,
    }),
    shallow,
  );
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
    favorites,
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
