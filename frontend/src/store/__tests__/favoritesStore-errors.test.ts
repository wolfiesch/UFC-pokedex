/**
 * Tests for favorites store error handling.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useFavoritesStore } from '../favoritesStore';
import * as api from '@/lib/api';
import type { FighterListItem } from '@/lib/types';


describe('FavoritesStore Error Handling', () => {
  const mockFighter: FighterListItem = {
    fighter_id: 'fighter-2',
    name: 'Test Fighter',
    nickname: 'The Test',
    division: 'Lightweight',
    record: { wins: 10, losses: 2, draws: 0 },
    is_current_champion: false,
    is_former_champion: false,
    image_url: null,
    detail_url: '/fighters/fighter-2',
  };

  beforeEach(() => {
    // Reset store state
    useFavoritesStore.setState({
      isInitialized: true,
      isLoading: false,
      defaultCollection: {
        collection_id: 1,
        title: 'Test Collection',
        user_id: 'demo-user',
        description: null,
        is_public: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        entries: [
          {
            id: 1,
            entry_id: 1,
            collection_id: 1,
            fighter_id: 'fighter-1',
            fighter_name: 'Fighter One',
            fighter: null,
            position: 1,
            notes: null,
            tags: [],
            created_at: new Date().toISOString(),
            added_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            metadata: {},
          },
        ],
      },
      error: null,
      searchTerm: '',
      stanceFilter: null,
      divisionFilter: null,
      championStatusFilters: [],
      winStreakCount: null,
      lossStreakCount: null,
    });

    // Reset mocks
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it('should return error result on toggle failure', async () => {
    // Mock _ensureDefaultCollection
    vi.spyOn(api, 'getFavoriteCollections').mockResolvedValue({
      collections: [{
        collection_id: 1,
        title: 'Test Collection',
        user_id: 'demo-user',
        description: null,
        is_public: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        entry_count: 0,
      }],
    });

    // Mock API to fail
    vi.spyOn(api, 'addFavoriteEntry').mockRejectedValue(
      new Error('Internal Server Error')
    );

    // Mock _refreshCollection to avoid timeout
    vi.spyOn(api, 'getFavoriteCollectionDetail').mockResolvedValue({
      collection_id: 1,
      title: 'Test Collection',
      user_id: 'demo-user',
      description: null,
      is_public: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      entries: [],
    });

    const { toggleFavorite } = useFavoritesStore.getState();
    const result = await toggleFavorite(mockFighter);

    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
  });

  it('should revert optimistic update on error', async () => {
    // Mock _ensureDefaultCollection
    vi.spyOn(api, 'getFavoriteCollections').mockResolvedValue({
      collections: [{
        collection_id: 1,
        title: 'Test Collection',
        user_id: 'demo-user',
        description: null,
        is_public: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        entry_count: 0,
      }],
    });

    // Mock API to fail
    vi.spyOn(api, 'addFavoriteEntry').mockRejectedValue(
      new Error('API Error')
    );

    // Mock _refreshCollection to restore state
    vi.spyOn(api, 'getFavoriteCollectionDetail').mockResolvedValue({
      collection_id: 1,
      title: 'Test Collection',
      user_id: 'demo-user',
      description: null,
      is_public: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      entries: [
        {
          id: 1,
          entry_id: 1,
          collection_id: 1,
          fighter_id: 'fighter-1',
          fighter_name: 'Fighter One',
          fighter: null,
          position: 1,
          notes: null,
          tags: [],
          created_at: new Date().toISOString(),
          added_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          metadata: {},
        },
      ],
    });

    const initialEntries = useFavoritesStore.getState().defaultCollection?.entries || [];
    const { toggleFavorite } = useFavoritesStore.getState();

    await toggleFavorite(mockFighter);

    // Should revert to initial state after refresh
    const finalEntries = useFavoritesStore.getState().defaultCollection?.entries || [];
    expect(finalEntries.length).toBe(initialEntries.length);
    expect(finalEntries[0].fighter_id).toBe('fighter-1');
  });
});
