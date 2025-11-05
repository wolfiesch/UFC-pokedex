"use client";

import { create } from "zustand";

import type { FighterListItem } from "@/lib/types";
import type { FavoriteCollectionDetail, FavoriteEntry } from "@/lib/types";
import {
  getFavoriteCollections,
  getFavoriteCollectionDetail,
  createFavoriteCollection,
  addFavoriteEntry,
  deleteFavoriteEntry,
} from "@/lib/api";
import { logger } from "@/lib/logger";

// Use demo user for development (in production, this would come from auth)
const DEMO_USER_ID =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_DEMO_FAVORITES_USER || "demo-user"
    : "demo-user";

const DEFAULT_COLLECTION_TITLE = "My Favorites";

type FavoritesState = {
  // Backend-synced state
  defaultCollection: FavoriteCollectionDetail | null;
  isLoading: boolean;
  isInitialized: boolean;
  error: string | null;

  // UI filter state (client-side only)
  searchTerm: string;
  stanceFilter: string | null;
  divisionFilter: string | null;
  championStatusFilters: string[];

  // Actions
  initialize: () => Promise<void>;
  toggleFavorite: (fighter: FighterListItem) => Promise<void>;
  isFavorite: (fighterId: string) => boolean;
  getFavorites: () => FighterListItem[];

  // Filter actions
  setSearchTerm: (term: string) => void;
  setStanceFilter: (stance: string | null) => void;
  setDivisionFilter: (division: string | null) => void;
  toggleChampionStatusFilter: (status: string) => void;

  // Internal helpers
  _ensureDefaultCollection: () => Promise<number>;
  _refreshCollection: () => Promise<void>;
};

export const useFavoritesStore = create<FavoritesState>((set, get) => ({
  // Initial state
  defaultCollection: null,
  isLoading: false,
  isInitialized: false,
  error: null,
  searchTerm: "",
  stanceFilter: null,
  divisionFilter: null,
  championStatusFilters: [],

  // Initialize the store by loading collections from backend
  initialize: async () => {
    const state = get();
    if (state.isInitialized || state.isLoading) {
      return; // Already initialized or loading
    }

    set({ isLoading: true, error: null });

    try {
      const response = await getFavoriteCollections(DEMO_USER_ID);

      // Find or create default collection
      let defaultCollection: FavoriteCollectionDetail | null = null;

      if (response.collections && response.collections.length > 0) {
        // Use first collection as default
        const firstCollectionId = response.collections[0].collection_id;
        defaultCollection = await getFavoriteCollectionDetail(
          firstCollectionId,
          DEMO_USER_ID
        );
      } else {
        // Create default collection if none exists
        logger.info("No collections found, creating default collection");
        const collectionId = await get()._ensureDefaultCollection();
        defaultCollection = await getFavoriteCollectionDetail(
          collectionId,
          DEMO_USER_ID
        );
      }

      set({
        defaultCollection,
        isLoading: false,
        isInitialized: true,
        error: null,
      });
    } catch (error) {
      logger.error("Failed to initialize favorites store", error);
      set({
        isLoading: false,
        isInitialized: true,
        error: error instanceof Error ? error.message : "Failed to load favorites",
      });
    }
  },

  // Ensure default collection exists, return its ID
  _ensureDefaultCollection: async () => {
    try {
      const response = await getFavoriteCollections(DEMO_USER_ID);

      if (response.collections && response.collections.length > 0) {
        return response.collections[0].collection_id;
      }

      // Create new default collection
      const newCollection = await createFavoriteCollection({
        user_id: DEMO_USER_ID,
        title: DEFAULT_COLLECTION_TITLE,
        description: "Your favorite UFC fighters",
        is_public: false,
      });

      return newCollection.collection_id;
    } catch (error) {
      logger.error("Failed to ensure default collection", error);
      throw error;
    }
  },

  // Refresh collection data from backend
  _refreshCollection: async () => {
    const state = get();
    if (!state.defaultCollection) {
      return;
    }

    try {
      const updatedCollection = await getFavoriteCollectionDetail(
        state.defaultCollection.collection_id,
        DEMO_USER_ID
      );
      set({ defaultCollection: updatedCollection, error: null });
    } catch (error) {
      logger.error("Failed to refresh collection", error);
      set({
        error: error instanceof Error ? error.message : "Failed to refresh favorites",
      });
    }
  },

  // Toggle favorite status for a fighter
  toggleFavorite: async (fighter: FighterListItem) => {
    const state = get();

    // Initialize if needed
    if (!state.isInitialized) {
      await get().initialize();
    }

    try {
      const collectionId = await get()._ensureDefaultCollection();
      const currentCollection = state.defaultCollection;
      const existingEntry = currentCollection?.entries?.find(
        (entry) => entry.fighter_id === fighter.fighter_id
      );

      if (existingEntry) {
        // Remove from favorites - optimistic update
        set({
          defaultCollection: currentCollection
            ? {
                ...currentCollection,
                entries: currentCollection.entries.filter(
                  (e) => e.fighter_id !== fighter.fighter_id
                ),
              }
            : null,
        });

        // Delete from backend
        await deleteFavoriteEntry(
          collectionId,
          existingEntry.entry_id,
          DEMO_USER_ID
        );
      } else {
        // Add to favorites - optimistic update
        const newEntry: FavoriteEntry = {
          entry_id: Date.now(), // Temporary ID for optimistic update
          collection_id: collectionId,
          fighter_id: fighter.fighter_id,
          fighter_name: fighter.name,
          fighter: fighter,
          position: (currentCollection?.entries?.length || 0) + 1,
          notes: null,
          tags: [],
          added_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          metadata: {},
        };

        set({
          defaultCollection: currentCollection
            ? {
                ...currentCollection,
                entries: [...currentCollection.entries, newEntry],
              }
            : null,
        });

        // Add to backend
        await addFavoriteEntry(
          collectionId,
          { fighter_id: fighter.fighter_id },
          DEMO_USER_ID
        );
      }

      // Refresh to get correct data from backend
      await get()._refreshCollection();
    } catch (error) {
      logger.error("Failed to toggle favorite", error);
      set({
        error: error instanceof Error ? error.message : "Failed to update favorite",
      });
      // Refresh collection to revert optimistic update
      await get()._refreshCollection();
    }
  },

  // Check if a fighter is favorited
  isFavorite: (fighterId: string) => {
    const state = get();
    return (
      state.defaultCollection?.entries?.some(
        (entry) => entry.fighter_id === fighterId
      ) || false
    );
  },

  // Get all favorited fighters
  getFavorites: () => {
    const state = get();
    if (!state.defaultCollection?.entries) {
      return [];
    }
    return state.defaultCollection.entries
      .map((entry) => entry.fighter)
      .filter((fighter): fighter is FighterListItem => fighter !== null);
  },

  // Filter setters
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
}));

// Helper hook with auto-initialization
export function useFavorites() {
  const store = useFavoritesStore();

  // Auto-initialize on first use
  if (typeof window !== "undefined" && !store.isInitialized && !store.isLoading) {
    store.initialize();
  }

  return store;
}
