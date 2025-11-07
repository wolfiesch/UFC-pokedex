export type FighterListItem = {
  fighter_id: string;
  detail_url: string;
  name: string;
  nickname?: string | null;
  record?: string | null;
  division?: string | null;
  height?: string | null;
  weight?: string | null;
  reach?: string | null;
  leg_reach?: string | null;
  stance?: string | null;
  dob?: string | null;
  image_url?: string | null;
  age?: number | null;
  is_current_champion?: boolean;
  is_former_champion?: boolean;
  was_interim?: boolean;
  /** Lightweight current streak summary provided by the list endpoint. */
  current_streak_type?: "win" | "loss" | "draw" | "none";
  current_streak_count?: number;
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
export type StatsSummaryMetricId =
  | "fighters_indexed"
  | "avg_sig_strikes_accuracy_pct"
  | "avg_takedown_accuracy_pct"
  | "avg_submission_attempts"
  | "avg_fight_duration_minutes"
  | "max_win_streak";

export type LeaderboardMetricId =
  | "sig_strikes_accuracy_pct"
  | "avg_submissions";

export interface StatsSummaryMetric {
  /** Machine-friendly metric identifier (e.g., `total_fights`). */
  id: StatsSummaryMetricId;
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
  metric_id: LeaderboardMetricId;
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

export interface FightGraphNode {
  fighter_id: string;
  name: string;
  division?: string | null;
  record?: string | null;
  image_url?: string | null;
  total_fights: number;
  latest_event_date?: string | null;
}

export type FightGraphResultBreakdown = Record<
  string,
  {
    win?: number;
    loss?: number;
    draw?: number;
    nc?: number;
    upcoming?: number;
    other?: number;
    [key: string]: number | undefined;
  }
>;

export interface FightGraphLink {
  source: string;
  target: string;
  fights: number;
  first_event_name?: string | null;
  first_event_date?: string | null;
  last_event_name?: string | null;
  last_event_date?: string | null;
  result_breakdown: FightGraphResultBreakdown;
}

export interface FightGraphResponse {
  nodes: FightGraphNode[];
  links: FightGraphLink[];
  metadata: Record<string, unknown>;
}

export interface FightGraphQueryParams {
  division?: string | null;
  startYear?: number | null;
  endYear?: number | null;
  limit?: number | null;
  includeUpcoming?: boolean;
}

export interface FighterComparisonEntry {
  fighter_id: string;
  name: string;
  record?: string | null;
  division?: string | null;
  age?: number | null;
  striking: Record<string, string | number | null | undefined>;
  grappling: Record<string, string | number | null | undefined>;
  significant_strikes: Record<string, string | number | null | undefined>;
  takedown_stats: Record<string, string | number | null | undefined>;
  career: Record<string, string | number | null | undefined>;
  is_current_champion?: boolean;
  is_former_champion?: boolean;
  was_interim?: boolean;
}

export interface FighterComparisonResponse {
  fighters: FighterComparisonEntry[];
}

/** Activity item surfaced in the favorites dashboard timeline. */
export interface FavoriteActivityItem {
  /** Surrogate key for the entry that triggered the activity. */
  entry_id: number;
  /** Fighter identifier associated with the activity. */
  fighter_id: string;
  /** Human-readable label describing what happened (added, updated, etc.). */
  action: string;
  /** ISO timestamp recording when the action took place. */
  occurred_at: string;
  /** Arbitrary structured metadata attached to the activity record. */
  metadata: Record<string, unknown>;
}

/** Upcoming fight metadata for any fighter inside a collection. */
export interface FavoriteUpcomingFight {
  fighter_id: string;
  opponent_name: string;
  event_name: string;
  event_date?: string | null;
  weight_class?: string | null;
}

/** Aggregated stats summarising an entire favorites collection. */
export interface FavoriteCollectionStats {
  total_fighters: number;
  win_rate: number;
  result_breakdown: Record<string, number>;
  divisions: string[];
  upcoming_fights: FavoriteUpcomingFight[];
}

/** Individual fighter entry within a favorites collection. */
export interface FavoriteEntry {
  id: number;
  entry_id: number;
  collection_id?: number;
  fighter_id: string;
  fighter_name?: string;
  fighter?: FighterListItem | null;
  position: number;
  notes?: string | null;
  tags: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  added_at?: string;
}

/** Lightweight collection representation used for listings. */
export interface FavoriteCollectionSummary {
  id: number;
  collection_id: number;
  user_id: string;
  title: string;
  description?: string | null;
  is_public: boolean;
  slug?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  stats?: FavoriteCollectionStats | null;
}

/** Fully-hydrated collection payload including entries and activity feed. */
export interface FavoriteCollectionDetail extends FavoriteCollectionSummary {
  entries: FavoriteEntry[];
  activity: FavoriteActivityItem[];
  stats: FavoriteCollectionStats;
}

/** Response payload returned from the favorites listing endpoint. */
export interface FavoriteCollectionListResponse {
  total: number;
  collections: FavoriteCollectionSummary[];
}

/** Client-side payload for creating a new favorites collection. */
export interface FavoriteCollectionCreatePayload {
  user_id: string;
  title: string;
  description?: string | null;
  is_public: boolean;
  slug?: string | null;
  metadata?: Record<string, never>;
}

/** Partial update payload for mutating collection metadata. */
export interface FavoriteCollectionUpdatePayload {
  title?: string;
  description?: string | null;
  is_public?: boolean;
  slug?: string | null;
  metadata?: Record<string, never>;
}

/** Payload used when inserting a fighter into a collection. */
export interface FavoriteEntryCreatePayload {
  fighter_id: string;
  position: number;
  notes?: string | null;
  tags?: string[];
  metadata?: Record<string, never>;
}

/** Partial update payload for an existing favorites entry. */
export interface FavoriteEntryUpdatePayload {
  position?: number | null;
  notes?: string | null;
  tags?: string[] | null;
  metadata?: Record<string, never> | null;
}

/** Payload used to persist drag-and-drop ordering changes. */
export interface FavoriteEntryReorderPayload {
  entry_ids: number[];
}
