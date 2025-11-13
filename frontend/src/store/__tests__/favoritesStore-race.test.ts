/**
 * Tests for favorites store race conditions.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { useFavoritesStore } from "../favoritesStore";
import * as api from "@/lib/api";

describe("FavoritesStore Race Conditions", () => {
  beforeEach(() => {
    // Reset store state completely
    useFavoritesStore.setState({
      isInitialized: false,
      isLoading: false,
      defaultCollection: null,
      favoriteIds: new Set(),
      favoriteEntryMap: new Map(),
      favoriteListCache: [],
      error: null,
    });

    // Reset mocks
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("should handle concurrent initialization calls", async () => {
    // Track API call count
    let apiCallCount = 0;
    let collectionDetailCallCount = 0;

    // Spy on getFavoriteCollections to count calls
    vi.spyOn(api, "getFavoriteCollections").mockImplementation(async () => {
      apiCallCount++;
      // Simulate async delay to expose race conditions
      await new Promise((resolve) => setTimeout(resolve, 50));
      // Return a collection so _ensureDefaultCollection doesn't make another call
      return {
        collections: [
          {
            collection_id: 1,
            title: "Test Collection",
            entry_count: 0,
            user_id: "demo-user",
            description: null,
            is_public: false,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ],
      };
    });

    vi.spyOn(api, "createFavoriteCollection").mockResolvedValue({
      collection_id: 1,
      title: "Test",
      user_id: "demo-user",
      description: null,
      is_public: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      entry_count: 0,
    });

    vi.spyOn(api, "getFavoriteCollectionDetail").mockImplementation(
      async () => {
        collectionDetailCallCount++;
        return {
          collection_id: 1,
          title: "Test",
          user_id: "demo-user",
          description: null,
          is_public: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          entries: [],
        };
      },
    );

    // Simulate 5 concurrent initialization calls
    const { initialize } = useFavoritesStore.getState();
    await Promise.all([
      initialize(),
      initialize(),
      initialize(),
      initialize(),
      initialize(),
    ]);

    // Should only make ONE API call despite concurrent requests
    expect(apiCallCount).toBe(1);
    expect(collectionDetailCallCount).toBe(1);
  });
});
