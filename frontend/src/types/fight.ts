/**
 * Shared fight-related domain models for frontend visualizations.
 * The structure mirrors the minimal payload delivered by the API so that
 * chart components can operate without additional transformations.
 */
export interface Fight {
  /** Unique fight identifier sourced from UFCStats or the internal DB. */
  id: string;
  /** ISO date string for the fight night. */
  date: string;
  /** Total fight duration in seconds (decisions set to the scheduled length). */
  finish_seconds: number;
  /** Finishing method bucket. */
  method: 'KO' | 'SUB' | 'DEC' | 'OTHER';
  /** Result from the perspective of the focus fighter. */
  result: 'W' | 'L' | 'D';
  /** Opponent unique identifier. */
  opponentId: string;
  /** Optimized WebP thumbnail path for the opponent headshot. */
  headshotUrl: string;
  /** Optional display label for the opponent; improves tooltip fidelity when available. */
  opponentName?: string;
  /** Optional event title for tooltip messaging. */
  eventName?: string;
  /** Optional UFC Stats or event URL for navigation. */
  eventUrl?: string;
  /** Optional fight round where the finish occurred. */
  round?: number;
  /** Optional clock string (e.g. `1:32`) at which the finish happened. */
  roundClock?: string;
}

export interface HexBinCell {
  /** Column index computed on the server for the density grid. */
  i: number;
  /** Row index computed on the server for the density grid. */
  j: number;
  /** Number of fights within the bucket. */
  count: number;
}
