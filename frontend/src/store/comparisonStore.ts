"use client";

import { createWithEqualityFn } from "zustand/traditional";
import { persist } from "zustand/middleware";

type ComparisonState = {
  comparisonList: string[]; // Array of fighter IDs (max 4)
  addToComparison: (fighterId: string) => void;
  removeFromComparison: (fighterId: string) => void;
  clearComparison: () => void;
  isInComparison: (fighterId: string) => boolean;
  canAddMore: () => boolean;
};

const MAX_COMPARISON = 4;

export const useComparisonStore = createWithEqualityFn<ComparisonState>()(
  persist(
    (set, get) => ({
      comparisonList: [],

      addToComparison: (fighterId) => {
        const list = get().comparisonList;
        if (list.length >= MAX_COMPARISON) {
          // Remove the oldest fighter if limit reached
          set({ comparisonList: [...list.slice(1), fighterId] });
        } else if (!list.includes(fighterId)) {
          set({ comparisonList: [...list, fighterId] });
        }
      },

      removeFromComparison: (fighterId) => {
        set({
          comparisonList: get().comparisonList.filter((id) => id !== fighterId)
        });
      },

      clearComparison: () => {
        set({ comparisonList: [] });
      },

      isInComparison: (fighterId) => {
        return get().comparisonList.includes(fighterId);
      },

      canAddMore: () => {
        return get().comparisonList.length < MAX_COMPARISON;
      },
    }),
    {
      name: "ufc-pokedex-comparison",
    },
  ),
);
