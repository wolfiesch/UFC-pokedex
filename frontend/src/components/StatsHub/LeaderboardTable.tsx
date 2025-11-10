"use client";

import Link from "next/link";

import type { LeaderboardEntry } from "@/lib/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

/**
 * Props describing the configuration for a leaderboard table instance. Each
 * table receives a set of ranked entries and optional metadata to drive
 * descriptive copy or support loading/error states.
 */
export interface LeaderboardTableProps {
  /** Title displayed above the leaderboard section. */
  title: string;
  /** Optional helper text to clarify the ranked metric. */
  description?: string;
  /**
   * Collection of ranked fighter entries. The order in the array determines the
   * displayed ranking (i.e. index + 1).
   */
  entries: LeaderboardEntry[];
  /** Column header label describing the metric being ranked. */
  metricLabel?: string;
  /** Flag used to toggle the loading placeholder state. */
  isLoading?: boolean;
  /** Optional error message displayed when data retrieval fails. */
  error?: string | null;
  /** Current pagination offset (used to display correct rank numbers). */
  offset?: number;
  /** Indicates if there are more entries available. */
  hasMore?: boolean;
  /** Callback to load more entries. */
  onLoadMore?: () => void;
}

/**
 * Lightweight helper that renders the leaderboard content area depending on the
 * state provided through the component props. Extracted to keep the JSX tidy.
 */
function renderLeaderboardBody({
  entries,
  metricLabel,
  offset = 0,
  hasMore = false,
  onLoadMore,
}: Pick<
  LeaderboardTableProps,
  "entries" | "metricLabel" | "offset" | "hasMore" | "onLoadMore"
>) {
  if (entries.length === 0) {
    return (
      <div className="py-6 text-center text-sm text-muted-foreground" role="status">
        No leaderboard data available yet. Check back soon as new fights are
        processed.
      </div>
    );
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-16">Rank</TableHead>
            <TableHead>Fighter</TableHead>
            <TableHead className="text-right">{metricLabel ?? "Score"}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map((entry, index) => {
            const rank = offset + index + 1;
            return (
              <TableRow key={`${entry.fighter_id}-${index}`}>
                <TableCell className="text-sm font-semibold">{rank}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    {entry.detail_url ? (
                      <Link
                        href={entry.detail_url}
                        className="font-medium text-foreground transition hover:text-foreground/70"
                      >
                        <span className="sr-only">View fighter profile:</span>
                        {entry.fighter_name}
                      </Link>
                    ) : (
                      <span>{entry.fighter_name}</span>
                    )}
                    {entry.fight_count != null && entry.fight_count < 5 && (
                      <span className="rounded-full bg-yellow-500/10 px-2 py-0.5 text-xs font-medium text-yellow-600 dark:text-yellow-400">
                        {entry.fight_count} {entry.fight_count === 1 ? "fight" : "fights"}
                      </span>
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-right font-mono text-sm font-semibold">
                  {entry.metric_value.toLocaleString(undefined, {
                    maximumFractionDigits: 2,
                  })}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      {hasMore && onLoadMore && (
        <div className="mt-4 flex justify-center">
          <button
            onClick={onLoadMore}
            className="rounded-full border border-border bg-card px-6 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
          >
            Show More
          </button>
        </div>
      )}
    </>
  );
}

/**
 * Accessible, composable leaderboard table tailored for the Stats Hub. It
 * exposes helper props for handling asynchronous states (loading, error, empty)
 * so the parent view can provide meaningful feedback to users.
 */
export default function LeaderboardTable({
  title,
  description,
  entries,
  metricLabel,
  isLoading = false,
  error,
  offset = 0,
  hasMore = false,
  onLoadMore,
}: LeaderboardTableProps) {
  return (
    <Card className="rounded-3xl border-border bg-card/80">
      <CardHeader className="space-y-2">
        <CardTitle className="text-xl">{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>
        {error ? (
          <div
            className="rounded-2xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive-foreground"
            role="alert"
          >
            {error}
          </div>
        ) : isLoading ? (
          <div className="py-6 text-center text-sm text-muted-foreground" role="status">
            Loading leaderboard…
          </div>
        ) : (
          renderLeaderboardBody({ entries, metricLabel, offset, hasMore, onLoadMore })
        )}
      </CardContent>
    </Card>
  );
}
