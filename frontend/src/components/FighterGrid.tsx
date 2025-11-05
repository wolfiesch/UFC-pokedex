"use client";

import type { ComponentType } from "react";
import { useEffect, useRef } from "react";
import dynamic from "next/dynamic";

import SkeletonFighterCard from "./SkeletonFighterCard";
import type { FighterListItem } from "@/lib/types";
import type { ApiError } from "@/lib/errors";

const EnhancedFighterCard = dynamic<ComponentType<{ fighter: FighterListItem }>>(
  () =>
    import("./fighter/EnhancedFighterCard").then((mod) => ({
      default: mod.EnhancedFighterCard,
    })),
  {
    loading: () => <SkeletonFighterCard />,
    ssr: false,
  }
);

type Props = {
  fighters: FighterListItem[];
  isLoading?: boolean;
  isLoadingMore?: boolean;
  error?: ApiError | null;
  total?: number;
  hasMore?: boolean;
  onLoadMore?: () => void;
  onRetry?: () => void;
  // For richer empty-states and clear CTA
  searchTerm?: string | null;
  stanceFilter?: string | null;
  divisionFilter?: string | null;
  onClearFilters?: () => void;
};

export default function FighterGrid({
  fighters,
  isLoading = false,
  isLoadingMore = false,
  error,
  total = 0,
  hasMore = false,
  onLoadMore,
  onRetry,
  searchTerm,
  stanceFilter,
  divisionFilter,
  onClearFilters,
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
      <div className="grid auto-rows-fr grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {[...Array(8)].map((_, i) => (
          <SkeletonFighterCard key={i} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-3xl border border-destructive/30 bg-destructive/10 p-6">
        <div className="mb-4 flex items-start gap-4">
          <div className="flex-shrink-0">
            <svg
              className="h-6 w-6 text-destructive"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="mb-1 font-semibold text-foreground">
              Unable to load fighters
            </h3>
            <p className="mb-2 text-sm text-foreground/80">
              {error.getUserMessage()}
            </p>

            {/* Technical details */}
            <details className="mb-4 text-xs text-foreground/70">
              <summary className="cursor-pointer hover:text-foreground">
                Technical Details
              </summary>
              <div className="mt-2 space-y-1 rounded-lg border border-destructive/20 bg-background/50 p-3 font-mono text-foreground/90">
                <p>
                  <span className="font-semibold">Error Type:</span> {error.errorType}
                </p>
                <p>
                  <span className="font-semibold">Status Code:</span> {error.statusCode}
                </p>
                {error.requestId && (
                  <p>
                    <span className="font-semibold">Request ID:</span> {error.requestId}
                  </p>
                )}
                {error.timestamp && (
                  <p>
                    <span className="font-semibold">Timestamp:</span>{" "}
                    {error.timestamp.toLocaleString()}
                  </p>
                )}
                {error.retryCount > 0 && (
                  <p>
                    <span className="font-semibold">Retry Attempts:</span> {error.retryCount}
                  </p>
                )}
                {error.retryAfter && (
                  <p>
                    <span className="font-semibold">Retry After:</span> {error.retryAfter}s
                  </p>
                )}
              </div>
            </details>

            <div className="flex gap-2">
              {onRetry && (
                <button
                  onClick={onRetry}
                  className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-destructive/90"
                >
                  Retry
                </button>
              )}
              {error.isRetryable && (
                <span className="flex items-center gap-1 rounded-full border border-destructive/20 bg-background/50 px-3 py-2 text-xs text-foreground/70">
                  <svg
                    className="h-3 w-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  This error may be temporary
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!fighters.length) {
    const hasFilters = Boolean((searchTerm ?? "").trim() || stanceFilter || divisionFilter);
    return (
      <div className="rounded-3xl border border-border bg-card/60 p-8 text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted/60">
          <svg
            className="h-8 w-8 text-muted-foreground"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <h3 className="mb-2 text-lg font-semibold text-foreground">No fighters found</h3>
        <p className="mb-4 text-sm text-muted-foreground">
          {hasFilters
            ? "No fighters match your current search and filters."
            : "We couldn't find any fighters at the moment."}
        </p>
        {hasFilters && onClearFilters ? (
          <button
            onClick={onClearFilters}
            className="mt-2 rounded-full border border-border bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          >
            Clear all filters
          </button>
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="grid auto-rows-fr grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {fighters.map((fighter) => (
          <EnhancedFighterCard key={fighter.fighter_id} fighter={fighter} />
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
