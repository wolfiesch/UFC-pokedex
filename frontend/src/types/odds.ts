export type OddsQualityTier =
  | "excellent"
  | "good"
  | "usable"
  | "poor"
  | "no_data";

export type OddsTimeSeriesPoint = {
  timestamp_ms: number;
  timestamp: string;
  odds: number;
};

export type ClosingRange = {
  start: string | null;
  end: string | null;
};

export type FighterOddsHistoryEntry = {
  id: string;
  opponent_name: string;
  event_name: string;
  event_date?: string | null;
  event_url?: string | null;
  opening_odds?: string | null;
  closing_range?: ClosingRange | null;
  num_odds_points: number;
  data_quality: OddsQualityTier;
};

export type FighterOddsHistoryResponse = {
  fighter_id: string;
  total_fights: number;
  returned: number;
  odds_history: FighterOddsHistoryEntry[];
};

export type FighterOddsChartFight = {
  fight_id: string;
  opponent: string;
  event: string;
  event_date?: string | null;
  event_url?: string | null;
  opening_odds?: string | null;
  closing_odds?: string | null;
  quality: OddsQualityTier;
  num_odds_points: number;
  time_series: OddsTimeSeriesPoint[];
};

export type FighterOddsChartResponse = {
  fighter_id: string;
  fights: FighterOddsChartFight[];
};

export type FightOddsDetailResponse = {
  id: string;
  fighter_id: string;
  opponent_name: string;
  event_name: string;
  event_date?: string | null;
  event_url?: string | null;
  opening_odds?: string | null;
  closing_range?: ClosingRange | null;
  mean_odds_history: OddsTimeSeriesPoint[];
  num_odds_points: number;
  data_quality: OddsQualityTier;
  scraped_at: string;
  bfo_fighter_url?: string | null;
};

export type OddsCoverageStats = {
  fighters_with_odds: number;
  total_fighters: number;
  coverage_percentage: number;
};

export type OddsQualityStatsResponse = {
  total_records: number;
  unique_fighters: number;
  avg_odds_points: number;
  quality_distribution: Record<string, number>;
  coverage_stats: OddsCoverageStats;
};
