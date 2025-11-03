export type FighterListItem = {
  fighter_id: string;
  detail_url: string;
  name: string;
  nickname?: string | null;
  division?: string | null;
  height?: string | null;
  weight?: string | null;
  reach?: string | null;
  stance?: string | null;
  dob?: string | null;
  image_url?: string | null;
};

export type FightHistoryEntry = {
  fight_id: string;
  event_name: string;
  event_date?: string | null;
  opponent: string;
  opponent_id?: string | null;
  result: string;
  method: string;
  round?: number | null;
  time?: string | null;
  fight_card_url?: string | null;
  stats?: Record<string, string | number | null | undefined>;
};

export type FighterDetail = FighterListItem & {
  record?: string | null;
  leg_reach?: string | null;
  age?: number | null;
  striking: Record<string, string | number | null | undefined>;
  grappling: Record<string, string | number | null | undefined>;
  significant_strikes: Record<string, string | number | null | undefined>;
  takedown_stats: Record<string, string | number | null | undefined>;
  career: Record<string, string | number | null | undefined>;
  fight_history: FightHistoryEntry[];
};

/**
 * Paginated subset of fighters returned from index and search endpoints.
 */
export interface PaginatedFightersResponse {
  fighters: FighterListItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

/**
 * Numerical key performance indicator (KPI) surfaced as part of the aggregated
 * statistics summary feed. Each metric is designed to provide a concise
 * high-level snapshot of platform-wide performance.
 */
export interface StatsSummaryMetric {
  /** Machine-friendly metric identifier (e.g., `total_fights`). */
  id: string;
  /** Human-readable label for visual display (e.g., `Total Fights`). */
  label: string;
  /** Primary numeric value associated with the KPI. */
  value: number;
  /** Optional clarifying detail describing how the KPI is calculated. */
  description?: string;
}

/**
 * Response payload returned by the `/stats/summary` endpoint. The API returns a
 * map of KPI identifiers to numeric values along with optional descriptive
 * metadata for each KPI.
 */
export interface StatsSummaryResponse {
  /** Aggregate metrics keyed by identifier. */
  metrics: StatsSummaryMetric[];
  /** Timestamp (ISO 8601) describing when the snapshot was generated. */
  generated_at?: string;
}

/**
 * Individual fighter entry used for leaderboard visualisations. The entry
 * captures rank, display name, and the numeric score being ranked.
 */
export interface LeaderboardEntry {
  /** Unique fighter identifier as provided by the backend dataset. */
  fighter_id: string;
  /** Linked fighter name for presenting in the leaderboard table UI. */
  fighter_name: string;
  /**
   * Numeric value used to order the leaderboard (e.g., total wins, finish rate
   * percentage). This value is shown alongside the fighter record.
   */
  metric_value: number;
  /** Optional direct link back to the fighter detail view. */
  detail_url?: string;
}

/**
 * A leaderboard groups fighters by a particular metric (wins, knockouts,
 * streaks, etc.) and presents a ranked list of competitors.
 */
export interface LeaderboardDefinition {
  /** Identifier for the metric powering the leaderboard. */
  metric_id: string;
  /** Title rendered above the leaderboard (e.g., `Top Finishers`). */
  title: string;
  /** Optional descriptive helper copy to provide extra context. */
  description?: string;
  /** Ordered list of fighters associated with the metric. */
  entries: LeaderboardEntry[];
}

/** Payload returned from `/stats/leaderboards`. */
export interface StatsLeaderboardsResponse {
  /** Collection of leaderboards grouped by metric. */
  leaderboards: LeaderboardDefinition[];
  /** ISO timestamp describing when the leaderboard snapshot was produced. */
  generated_at?: string;
}

/**
 * Data point used to render a trend line on the time-series chart.
 */
export interface TrendPoint {
  /** ISO 8601 timestamp or simple date string describing the observation. */
  timestamp: string;
  /** Numeric value observed at the given timestamp. */
  value: number;
}

/**
 * Series definition representing a tracked metric (wins per month, signiﬁcant
 * strikes, etc.) for a given entity. Multiple series can be plotted together to
 * compare trajectories.
 */
export interface TrendSeries {
  /** Identifier describing the metric (e.g., `monthly_finishes`). */
  metric_id: string;
  /** Optional identifier for the fighter or group represented by the series. */
  fighter_id?: string;
  /** Human-readable name for the plotted series. */
  label: string;
  /** Chronological list of observations for the series. */
  points: TrendPoint[];
}

/** Response payload returned from `/stats/trends`. */
export interface StatsTrendsResponse {
  /** Collection of time-series data grouped by metric and/or fighter. */
  trends: TrendSeries[];
  /** ISO timestamp describing when the trend dataset was generated. */
  generated_at?: string;
}

export interface FighterComparisonEntry {
  fighter_id: string;
  name: string;
  record?: string | null;
  division?: string | null;
  striking: Record<string, string | number | null | undefined>;
  grappling: Record<string, string | number | null | undefined>;
  significant_strikes: Record<string, string | number | null | undefined>;
  takedown_stats: Record<string, string | number | null | undefined>;
  career: Record<string, string | number | null | undefined>;
}

export interface FighterComparisonResponse {
  fighters: FighterComparisonEntry[];
}
