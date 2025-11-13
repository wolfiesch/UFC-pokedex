"use client";

import { useCallback } from "react";
import { toast } from "sonner";
import { useComparisonStore } from "@/store/comparisonStore";

interface UseComparisonResult {
  comparisonList: string[];
  addToComparison: (fighterId: string, fighterName?: string) => void;
  removeFromComparison: (fighterId: string, fighterName?: string) => void;
  toggleComparison: (fighterId: string, fighterName?: string) => void;
  clearComparison: () => void;
  isInComparison: (fighterId: string) => boolean;
  canAddMore: () => boolean;
}

/**
 * Hook that wraps the comparison store with toast notifications
 * Provides a user-friendly interface for managing fighter comparisons
 *
 * @example
 * ```tsx
 * const { addToComparison, removeFromComparison, isInComparison } = useComparison();
 *
 * <button onClick={() => addToComparison(fighter.fighter_id, fighter.name)}>
 *   Add to Comparison
 * </button>
 * ```
 */
export function useComparison(): UseComparisonResult {
  const store = useComparisonStore();

  const addToComparison = useCallback(
    (fighterId: string, fighterName?: string) => {
      const wasAtLimit = !store.canAddMore();

      store.addToComparison(fighterId);

      if (wasAtLimit) {
        toast("Comparison updated", {
          description: `Removed oldest fighter and added ${fighterName || "fighter"}`,
        });
      } else {
        toast.success(`Added to comparison`, {
          description: fighterName
            ? `${fighterName} added to comparison list`
            : "Fighter added to comparison list",
        });
      }
    },
    [store],
  );

  const removeFromComparison = useCallback(
    (fighterId: string, fighterName?: string) => {
      store.removeFromComparison(fighterId);

      toast(`Removed from comparison`, {
        description: fighterName
          ? `${fighterName} removed from comparison list`
          : "Fighter removed from comparison list",
      });
    },
    [store],
  );

  const toggleComparison = useCallback(
    (fighterId: string, fighterName?: string) => {
      if (store.isInComparison(fighterId)) {
        removeFromComparison(fighterId, fighterName);
      } else {
        addToComparison(fighterId, fighterName);
      }
    },
    [store, addToComparison, removeFromComparison],
  );

  const clearComparison = useCallback(() => {
    store.clearComparison();
    toast("Comparison cleared", {
      description: "All fighters removed from comparison list",
    });
  }, [store]);

  return {
    comparisonList: store.comparisonList,
    addToComparison,
    removeFromComparison,
    toggleComparison,
    clearComparison,
    isInComparison: store.isInComparison,
    canAddMore: store.canAddMore,
  };
}
