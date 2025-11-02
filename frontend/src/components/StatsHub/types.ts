/**
 * Shared type definitions for the Stats Hub presentational components.
 *
 * The interfaces below intentionally capture the pre-aggregated metrics that the
 * backend exposes so our tests can render deterministic mock leaderboards and
 * performance trends.
 */

/** Represents a single row in a leaderboard style visualization. */
export type LeaderboardEntry = {
  fighterId: string;
  fighterName: string;
  metricLabel: string;
  metricValue: number;
  /** Optional delta value used to show improvement over the previous sample. */
  delta?: number;
};

/** Represents a single point within a trend or sparkline. */
export type TrendPoint = {
  /** Human readable label, typically a month name. */
  label: string;
  /** Numeric metric value at the given point in time. */
  value: number;
};

/**
 * A trend series aggregates points for one fighter/metric combination.
 * Each series is rendered as a column so we can compare multiple fighters.
 */
export type TrendSeries = {
  fighterId: string;
  fighterName: string;
  metricLabel: string;
  points: TrendPoint[];
};
