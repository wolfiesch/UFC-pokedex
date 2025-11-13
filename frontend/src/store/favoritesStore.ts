"use client";

import { createWithEqualityFn } from "zustand/traditional";

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

type DerivedFavoritesSnapshot = {
  defaultCollection: FavoriteCollectionDetail | null;
  favoriteIds: Set<string>;
  favoriteEntryMap: Map<string, FavoriteEntry>;
  favoriteListCache: FighterListItem[];
};

function deriveFavoritesSnapshot(
  collection: FavoriteCollectionDetail | null,
): DerivedFavoritesSnapshot {
  if (!collection?.entries?.length) {
    return {
      defaultCollection: collection,
      favoriteIds: new Set<string>(),
      favoriteEntryMap: new Map<string, FavoriteEntry>(),
      favoriteListCache: [],
    };
  }

  const favoriteIds = new Set<string>();
  const favoriteEntryMap = new Map<string, FavoriteEntry>();
  const favoriteListCache: FighterListItem[] = [];

  for (const entry of collection.entries) {
    favoriteIds.add(entry.fighter_id);
    favoriteEntryMap.set(entry.fighter_id, entry);
    if (entry.fighter) {
      favoriteListCache.push(entry.fighter);
    }
  }

  return {
    defaultCollection: collection,
    favoriteIds,
    favoriteEntryMap,
    favoriteListCache,
  };
}

// Add outside the store - promise-based initialization lock
let initializationPromise: Promise<void> | null = null;

type FavoritesState = {
  // Backend-synced state
  defaultCollection: FavoriteCollectionDetail | null;
  favoriteIds: Set<string>;
  favoriteEntryMap: Map<string, FavoriteEntry>;
  favoriteListCache: FighterListItem[];
  isLoading: boolean;
  isInitialized: boolean;
  error: string | null;

  // Actions
  initialize: () => Promise<void>;
  toggleFavorite: (
    fighter: FighterListItem,
  ) => Promise<{ success: boolean; error?: string }>;
  isFavorite: (fighterId: string) => boolean;
  getFavorites: () => FighterListItem[];

  // Internal helpers
  _ensureDefaultCollection: () => Promise<number>;
  _refreshCollection: () => Promise<void>;
};

const initialDerivedState = deriveFavoritesSnapshot(null);

export const useFavoritesStore = createWithEqualityFn<FavoritesState>(
  (set, get) => ({
    // Initial state
    ...initialDerivedState,
    isLoading: false,
    isInitialized: false,
    error: null,

    // Initialize the store by loading collections from backend
    initialize: async () => {
      const state = get();

      // If already initialized, return immediately
      if (state.isInitialized) {
        return;
      }

      // If initialization is in progress, wait for it
      if (initializationPromise) {
        return initializationPromise;
      }

      // Set the promise IMMEDIATELY before any async operations
      // This prevents race conditions where multiple calls check before it's set
      initializationPromise = (async () => {
        // Start initialization
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
              DEMO_USER_ID,
            );
          } else {
            // Create default collection if none exists
            logger.info("No collections found, creating default collection");
            const collectionId = await get()._ensureDefaultCollection();
            defaultCollection = await getFavoriteCollectionDetail(
              collectionId,
              DEMO_USER_ID,
            );
          }

          set({
            ...deriveFavoritesSnapshot(defaultCollection),
            isLoading: false,
            isInitialized: true,
            error: null,
          });
        } catch (error) {
          logger.error(
            "Failed to initialize favorites store",
            error instanceof Error ? error : undefined,
          );
          set({
            isLoading: false,
            isInitialized: true,
            error:
              error instanceof Error
                ? error.message
                : "Failed to load favorites",
          });
        } finally {
          // Clear the promise when done
          initializationPromise = null;
        }
      })();

      return initializationPromise;
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
        logger.error(
          "Failed to ensure default collection",
          error instanceof Error ? error : undefined,
        );
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
          DEMO_USER_ID,
        );
        set({
          ...deriveFavoritesSnapshot(updatedCollection),
          error: null,
        });
      } catch (error) {
        logger.error(
          "Failed to refresh collection",
          error instanceof Error ? error : undefined,
        );
        set({
          error:
            error instanceof Error
              ? error.message
              : "Failed to refresh favorites",
        });
      }
    },

    // Toggle favorite status for a fighter
    toggleFavorite: async (
      fighter: FighterListItem,
    ): Promise<{ success: boolean; error?: string }> => {
      if (!get().isInitialized) {
        await get().initialize();
      }

      try {
        const collectionId = await get()._ensureDefaultCollection();
        const { favoriteEntryMap } = get();
        const existingEntry = favoriteEntryMap.get(fighter.fighter_id);

        if (existingEntry) {
          // Remove from favorites - optimistic update
          set((store) => {
            if (!store.defaultCollection) {
              return {};
            }

            const updatedCollection: FavoriteCollectionDetail = {
              ...store.defaultCollection,
              entries: store.defaultCollection.entries.filter(
                (entry) => entry.fighter_id !== fighter.fighter_id,
              ),
            };

            return deriveFavoritesSnapshot(updatedCollection);
          });

          await deleteFavoriteEntry(
            collectionId,
            existingEntry.entry_id,
            DEMO_USER_ID,
          );
        } else {
          const now = new Date().toISOString();
          const tempId = Date.now();

          set((store) => {
            if (!store.defaultCollection) {
              return {};
            }

            const newEntry: FavoriteEntry = {
              id: tempId,
              entry_id: tempId,
              collection_id: collectionId,
              fighter_id: fighter.fighter_id,
              fighter_name: fighter.name,
              fighter,
              position: store.defaultCollection.entries.length + 1,
              notes: null,
              tags: [],
              created_at: now,
              added_at: now,
              updated_at: now,
              metadata: {},
            };

            const updatedCollection: FavoriteCollectionDetail = {
              ...store.defaultCollection,
              entries: [...store.defaultCollection.entries, newEntry],
            };

            return deriveFavoritesSnapshot(updatedCollection);
          });

          await addFavoriteEntry(
            collectionId,
            { fighter_id: fighter.fighter_id },
            DEMO_USER_ID,
          );
        }

        await get()._refreshCollection();

        return { success: true };
      } catch (error) {
        logger.error(
          "Failed to toggle favorite",
          error instanceof Error ? error : undefined,
        );
        set({
          error:
            error instanceof Error
              ? error.message
              : "Failed to update favorite",
        });
        await get()._refreshCollection();

        return {
          success: false,
          error: error instanceof Error ? error.message : "Unknown error",
        };
      }
    },

    // Check if a fighter is favorited
    isFavorite: (fighterId: string) => get().favoriteIds.has(fighterId),

    // Get all favorited fighters
    getFavorites: () => get().favoriteListCache,
  }),
);

// Helper hook with auto-initialization
export function useFavorites() {
  const store = useFavoritesStore();

  // Auto-initialize on first use
  if (
    typeof window !== "undefined" &&
    !store.isInitialized &&
    !store.isLoading
  ) {
    store.initialize();
  }

  return store;
}
