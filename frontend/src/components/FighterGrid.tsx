"use client";

import { EnhancedFighterCard } from "./fighter/EnhancedFighterCard";
import SkeletonFighterCard from "./SkeletonFighterCard";
import type { FighterListItem } from "@/lib/types";
import type { ApiError } from "@/lib/errors";

/**
 * Props shared by the paginated roster grid. The component stays presentation
 * focused by accepting pre-computed pagination state (limit, offset, etc.) and
 * emitting callbacks for navigation actions.
 */
type Props = {
  fighters: FighterListItem[];
  isLoading?: boolean;
  isFetchingPage?: boolean;
  error?: ApiError | null;
  total?: number;
  limit: number;
  offset: number;
  canNextPage?: boolean;
  canPreviousPage?: boolean;
  onNextPage?: () => void;
  onPreviousPage?: () => void;
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
  isFetchingPage = false,
  error,
  total = 0,
  limit,
  offset,
  canNextPage = false,
  canPreviousPage = false,
  onNextPage,
  onPreviousPage,
  onRetry,
  searchTerm,
  stanceFilter,
  divisionFilter,
  onClearFilters,
}: Props) {
  const safeLimit = Math.max(1, Number.isFinite(limit) ? Math.trunc(limit) : 1);
  const safeOffset = Math.max(0, Number.isFinite(offset) ? Math.trunc(offset) : 0);
  const currentPage = Math.max(1, Math.floor(safeOffset / safeLimit) + 1);
  const totalPages = Math.max(1, Math.ceil(total / safeLimit));
  const startIndex = total === 0 ? 0 : safeOffset + 1;
  const endIndex = total === 0 ? 0 : Math.min(safeOffset + fighters.length, total);

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

      <div className="rounded-3xl border border-border bg-card/60 p-4 shadow-subtle">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm text-muted-foreground">
            {total === 0 ? (
              "No fighters to display"
            ) : (
              <span>
                Showing {startIndex.toLocaleString()}-{endIndex.toLocaleString()} of {total.toLocaleString()} fighters
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onPreviousPage}
              disabled={!canPreviousPage || isFetchingPage}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
            >
              <svg
                className="h-4 w-4"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
              </svg>
              Prev
            </button>
            <span className="text-xs font-semibold uppercase tracking-[0.4em] text-muted-foreground">
              Page {Math.min(currentPage, totalPages)} of {totalPages}
            </span>
            <button
              type="button"
              onClick={onNextPage}
              disabled={!canNextPage || isFetchingPage}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
            >
              Next
              <svg
                className="h-4 w-4"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </button>
            {isFetchingPage ? (
              <span
                className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground/40 border-t-foreground"
                aria-label="Loading page"
              />
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
