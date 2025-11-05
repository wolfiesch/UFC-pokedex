/**
 * @fileoverview Shared Fight domain types used across the analytics visualization suite.
 * The verbose inline documentation is intentional per project guidelines so future
 * contributors can understand the data contracts without referencing backends.
 */

/**
 * Enumerates the known fight conclusion methods that can be rendered by the analytics layer.
 */
export type FightMethod = 'KO' | 'SUB' | 'DEC' | 'OTHER';

/**
 * Enumerates the possible fight results from the perspective of the profiled fighter.
 */
export type FightResult = 'W' | 'L' | 'D';

/**
 * Minimal payload describing a fight instance for scatter/heatmap analytics.
 * Optional descriptive metadata is included when available so tooltips can surface
 * richer context without the component having to re-fetch additional resources.
 */
export interface Fight {
  /** Globally unique identifier for the fight (typically a UUID or UFCStats slug). */
  id: string;
  /** ISO timestamp (YYYY-MM-DD or full ISO string) representing the event date. */
  date: string;
  /**
   * Duration until the finish measured in seconds.
   * Decisions should map to the maximum scheduled fight time (e.g., 3x5 min = 900s).
   */
  finish_seconds: number;
  /** How the fight ended (knockout, submission, decision, or other). */
  method: FightMethod;
  /** Whether the profiled fighter won, lost, or drew. */
  result: FightResult;
  /** Stable identifier for the opponent used to map cached headshots. */
  opponentId: string;
  /** CDN URL pointing to a 32–48px WebP headshot for the opponent. */
  headshotUrl: string;
  /** Optional opponent display name for richer tooltips. */
  opponentName?: string;
  /** Optional event name or card title. */
  eventName?: string;
  /** Optional scheduled rounds information for tooltip presentation. */
  scheduledRounds?: number;
  /** Optional finishing round (if applicable). */
  finishRound?: number;
  /** Optional formatted time string (MM:SS) representing the finish moment inside the round. */
  finishRoundTime?: string;
  /** Optional canonical UFCStats URL for deep linking in tooltips. */
  ufcStatsUrl?: string;
}
