"use client";

import { useEffect, useRef } from "react";
import FighterCard from "./FighterCard";
import type { FighterListItem } from "@/lib/types";

type Props = {
  fighters: FighterListItem[];
  isLoading?: boolean;
  isLoadingMore?: boolean;
  error?: string | null;
  total?: number;
  hasMore?: boolean;
  onLoadMore?: () => void;
};

export default function FighterGrid({
  fighters,
  isLoading = false,
  isLoadingMore = false,
  error,
  total = 0,
  hasMore = false,
  onLoadMore,
}: Props) {
  const sentinelRef = useRef<HTMLDivElement>(null);

  // Intersection Observer for infinite scroll
  useEffect(() => {
    if (!sentinelRef.current || !hasMore || isLoadingMore || !onLoadMore) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          onLoadMore();
        }
      },
      { rootMargin: "200px" } // Trigger 200px before reaching bottom
    );

    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [hasMore, isLoadingMore, onLoadMore]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-3xl border border-border bg-card/60 p-8 text-sm text-muted-foreground">
        <span className="inline-flex h-6 w-6 animate-spin rounded-full border-2 border-muted-foreground/40 border-t-foreground" />
        Loading fighters…
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-3xl border border-destructive/30 bg-destructive/10 p-6 text-sm text-destructive-foreground">
        Unable to load fighters right now. Error: {error}
      </div>
    );
  }

  if (!fighters.length) {
    return (
      <div className="rounded-3xl border border-border bg-card/60 p-6 text-center text-sm text-muted-foreground">
        No fighters found. Try a different search.
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {fighters.map((fighter) => (
          <FighterCard key={fighter.fighter_id} fighter={fighter} />
        ))}
      </div>

      {/* Loading indicator */}
      {isLoadingMore && (
        <div className="flex items-center justify-center gap-3 rounded-3xl border border-border bg-card/60 py-6 text-sm text-muted-foreground">
          <span className="inline-flex h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground/40 border-t-foreground" />
          Loading more fighters…
        </div>
      )}

      {/* Total count display */}
      {!isLoadingMore && fighters.length > 0 && (
        <div className="border-t border-border pt-6 text-center text-sm text-muted-foreground">
          Showing {fighters.length} of {total} fighters
        </div>
      )}

      {/* End of list message */}
      {!hasMore && fighters.length > 0 && (
        <div className="text-center text-sm text-muted-foreground">
          All fighters loaded
        </div>
      )}

      {/* Sentinel div for intersection observer */}
      <div ref={sentinelRef} className="h-4" />
    </div>
  );
}
