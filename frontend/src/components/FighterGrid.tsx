"use client";

import FighterCard from "./FighterCard";
import type { FighterListItem } from "@/lib/types";

type Props = {
  fighters: FighterListItem[];
  isLoading?: boolean;
  error?: string | null;
  // Pagination props
  total?: number;
  offset?: number;
  limit?: number;
  hasMore?: boolean;
  onNextPage?: () => void;
  onPrevPage?: () => void;
};

export default function FighterGrid({
  fighters,
  isLoading = false,
  error,
  total = 0,
  offset = 0,
  limit = 20,
  hasMore = false,
  onNextPage,
  onPrevPage,
}: Props) {
  if (isLoading) {
    return <p className="text-slate-300">Loading fighters...</p>;
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-900/60 bg-red-950/40 p-4 text-sm text-red-200">
        Unable to load fighters right now. Error: {error}
      </div>
    );
  }

  if (!fighters.length) {
    return <p className="text-slate-500">No fighters found. Try a different search.</p>;
  }

  const showPagination = onNextPage && onPrevPage && total > 0;
  const pageSize = limit > 0 ? limit : 20;
  const currentPage = Math.floor(offset / pageSize) + 1;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {fighters.map((fighter) => (
          <FighterCard key={fighter.fighter_id} fighter={fighter} />
        ))}
      </div>

      {showPagination && (
        <div className="mt-8 flex items-center justify-between border-t border-slate-700 pt-6">
          <button
            onClick={onPrevPage}
            disabled={offset === 0}
            className="rounded-lg bg-pokedexBlue px-4 py-2 text-white transition-colors hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-pokedexBlue"
          >
            ← Previous
          </button>

          <span className="text-sm text-slate-400">
            Page {currentPage} of {totalPages} • Showing {offset + 1}-
            {Math.min(offset + fighters.length, total)} of {total} fighters
          </span>

          <button
            onClick={onNextPage}
            disabled={!hasMore}
            className="rounded-lg bg-pokedexBlue px-4 py-2 text-white transition-colors hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-pokedexBlue"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
