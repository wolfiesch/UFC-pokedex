import type { FightGraphNode, FightWebSortOption } from "@/lib/types";

export const DEFAULT_SORT: FightWebSortOption = "most_active";

export const FIGHT_WEB_SORT_OPTIONS: Record<
  FightWebSortOption,
  {
    label: string;
    description: string;
  }
> = {
  most_active: {
    label: "Most Active",
    description: "Highest total fights first",
  },
  alphabetical: {
    label: "Alphabetical",
    description: "Order by fighter name A-Z",
  },
  most_recent: {
    label: "Most Recent",
    description: "Newest/latest fight dates first",
  },
} as const;

export function isValidFightWebSortOption(
  value: unknown,
): value is FightWebSortOption {
  if (typeof value !== "string") {
    return false;
  }
  return value in FIGHT_WEB_SORT_OPTIONS;
}

export function sortFightWebNodes(
  nodes: FightGraphNode[],
  sortBy: FightWebSortOption,
): FightGraphNode[] {
  const sorted = [...nodes];

  switch (sortBy) {
    case "alphabetical": {
      return sorted.sort((a, b) => a.name.localeCompare(b.name));
    }
    case "most_recent": {
      return sorted.sort((a, b) => {
        const aDate = a.latest_event_date;
        const bDate = b.latest_event_date;

        if (aDate && bDate) {
          const dateCompare = bDate.localeCompare(aDate);
          if (dateCompare !== 0) {
            return dateCompare;
          }
        } else if (!aDate && bDate) {
          return 1;
        } else if (aDate && !bDate) {
          return -1;
        }

        return a.name.localeCompare(b.name);
      });
    }
    case "most_active":
    default: {
      return sorted.sort((a, b) => {
        if (b.total_fights !== a.total_fights) {
          return b.total_fights - a.total_fights;
        }
        return a.name.localeCompare(b.name);
      });
    }
  }
}
