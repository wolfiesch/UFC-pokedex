"use client";

import Image from "next/image";
import { useEffect, useMemo, useRef } from "react";

import { FighterImagePlaceholder } from "../FighterImagePlaceholder";

/**
 * Lightweight descriptor for an upcoming booked fight displayed within the insight card.
 * The string-based fields intentionally accept `null` to mirror data returned by UFC Stats
 * without forcing additional normalization in the graph layer.
 */
export interface UpcomingBoutSummary {
  /** ISO-8601 date string describing when the bout is scheduled to occur. */
  date?: string | null;
  /** Human-readable event title pulled directly from the fight history feed. */
  event?: string | null;
  /** Name of the opponent for the scheduled matchup. */
  opponent?: string | null;
}

/**
 * Information bundle required for rendering the fighter overview panel.  The data keeps the
 * optional shape of API payloads so the component can gracefully fallback when details are
 * unavailable (e.g., when the hover fetch fails or is still loading).
 */
export interface FighterInsightMetadata {
  /** Database identifier for the fighter (used for keying and navigation). */
  id: string;
  /** Display name shown at the top of the card. */
  name: string;
  /** Fully qualified image URL (or `null` if no portrait exists). */
  imageUrl?: string | null;
  /** Lightweight record summary (e.g., `25-4-0`). */
  record?: string | null;
  /** Weight class or division label. */
  division?: string | null;
  /**
   * Human readable streak label ("Win Streak – 3"), emitted by the calling view so the card does
   * not need to replicate formatting logic.
   */
  streakLabel?: string | null;
  /**
   * Classification of the streak for styling.  Matches backend enumerations so future themes can
   * map to win/loss/draw palettes consistently.
   */
  streakType?: "win" | "loss" | "draw" | "none" | null;
  /** Chronologically sorted list of upcoming bouts associated with the fighter. */
  upcomingBouts?: UpcomingBoutSummary[] | null;
}

export interface FighterInsightCardProps {
  /** Metadata bundle describing the fighter currently highlighted in the graph. */
  fighter: FighterInsightMetadata;
  /** Optional copy used to highlight backend request state (e.g., `Loading details…`). */
  statusMessage?: string | null;
  /** When true the component shifts to a skeleton/disabled state while data loads. */
  isLoading?: boolean;
  /**
   * Callback invoked when the "Open profile" quick action is triggered.  Consumers typically
   * navigate to the fighter detail page.
   */
  onOpenProfile?: () => void;
  /**
   * Callback invoked when the "Filter by division" quick action fires.  The parent view wires this
   * up to FightWeb's division filter controls.
   */
  onFilterDivision?: () => void;
  /**
   * Hint describing how the card was opened.  Keyboard-triggered cards auto-focus the first quick
   * action so screen reader and keyboard users land on an interactive control immediately.
   */
  interactionMode?: "pointer" | "keyboard" | "selection" | null;
  /**
   * Ref registration callback supplied by the positioning layer so it can measure the rendered
   * dimensions for collision handling.
   */
  registerCard?: (element: HTMLDivElement | null) => void;
}

/**
 * Render a rich tooltip-style card for the fight graph that exposes upcoming fights, the current
 * streak, and quick access actions.  The card doubles as a focusable popover so keyboard and assistive
 * technology users can explore the network without relying on pointer interactions.
 */
export function FighterInsightCard({
  fighter,
  statusMessage,
  isLoading = false,
  onOpenProfile,
  onFilterDivision,
  interactionMode = null,
  registerCard,
}: FighterInsightCardProps) {
  const firstActionRef = useRef<HTMLButtonElement | null>(null);

  // Capture focus when opened via keyboard to ensure the quick actions are reachable without a mouse.
  useEffect(() => {
    if (interactionMode === "keyboard" && firstActionRef.current) {
      firstActionRef.current.focus({ preventScroll: true });
    }
  }, [interactionMode]);

  const upcomingBouts = useMemo(() => {
    if (!fighter.upcomingBouts || fighter.upcomingBouts.length === 0) {
      return [];
    }
    return fighter.upcomingBouts.filter((bout) => {
      return (
        (bout.event && bout.event.trim().length > 0) ||
        (bout.opponent && bout.opponent.trim().length > 0) ||
        (bout.date && bout.date.trim().length > 0)
      );
    });
  }, [fighter.upcomingBouts]);

  const streakBadgeClass = useMemo(() => {
    switch (fighter.streakType) {
      case "win":
        return "bg-emerald-500/10 text-emerald-500 border-emerald-500/30";
      case "loss":
        return "bg-rose-500/10 text-rose-500 border-rose-500/30";
      case "draw":
        return "bg-sky-500/10 text-sky-500 border-sky-500/30";
      default:
        return "bg-muted text-muted-foreground border-border/80";
    }
  }, [fighter.streakType]);

  return (
    <div
      ref={registerCard}
      className="w-72 max-w-[18.5rem] rounded-2xl border border-border/60 bg-card/95 p-4 text-sm shadow-2xl outline-none"
      role="dialog"
      aria-modal="false"
      aria-label={`${fighter.name} insight card`}
    >
      <div className="flex items-start gap-3">
        <div className="relative h-16 w-16 overflow-hidden rounded-xl border border-border/60 bg-muted/40">
          {fighter.imageUrl ? (
            <Image
              src={fighter.imageUrl}
              alt={fighter.name}
              fill
              sizes="64px"
              className="object-cover"
            />
          ) : (
            <FighterImagePlaceholder className="h-full w-full" name={fighter.name} />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-base font-semibold leading-tight">
            {fighter.name}
          </p>
          <p className="text-xs text-muted-foreground/80">
            {fighter.division ?? "Division unknown"}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {fighter.record ?? "Record unavailable"}
          </p>
          {fighter.streakLabel ? (
            <span
              className={`mt-2 inline-flex items-center gap-2 rounded-full border px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide ${streakBadgeClass}`}
            >
              {fighter.streakLabel}
            </span>
          ) : null}
        </div>
      </div>

      <div className="mt-4 space-y-2">
        <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.25em] text-muted-foreground/70">
          <span>Quick actions</span>
          {statusMessage ? (
            <span className="text-[10px] lowercase text-muted-foreground/60">
              {statusMessage}
            </span>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            ref={firstActionRef}
            type="button"
            onClick={onOpenProfile}
            className="flex-1 rounded-lg border border-border/70 bg-background/80 px-3 py-2 text-left text-xs font-medium text-foreground shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background hover:border-border"
          >
            Open profile
          </button>
          <button
            type="button"
            onClick={onFilterDivision}
            className="flex-1 rounded-lg border border-border/70 bg-background/80 px-3 py-2 text-left text-xs font-medium text-foreground shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background hover:border-border"
            disabled={!fighter.division}
            aria-disabled={!fighter.division}
          >
            Filter by division
          </button>
        </div>
      </div>

      <div className="mt-4">
        <div className="text-[11px] uppercase tracking-[0.25em] text-muted-foreground/70">
          Upcoming bouts
        </div>
        {isLoading ? (
          <div className="mt-2 space-y-2">
            <div className="h-3 rounded bg-muted/60" />
            <div className="h-3 rounded bg-muted/40" />
          </div>
        ) : upcomingBouts.length > 0 ? (
          <ul className="mt-2 space-y-2 text-xs text-muted-foreground">
            {upcomingBouts.slice(0, 3).map((bout, index) => (
              <li key={`${bout.event ?? "event"}-${index}`} className="rounded-lg border border-border/60 bg-background/60 p-2">
                <div className="font-medium text-foreground/90">
                  {bout.opponent ?? "Opponent TBA"}
                </div>
                <div className="text-[11px] text-muted-foreground/80">
                  {bout.event ?? "Event TBA"}
                </div>
                {bout.date ? (
                  <div className="text-[11px] text-muted-foreground/70">
                    {new Date(bout.date).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 rounded-lg border border-dashed border-border/60 bg-muted/20 p-3 text-xs text-muted-foreground/80">
            No scheduled bouts at the moment.
          </p>
        )}
      </div>
    </div>
  );
}
