import type { LeaderboardMetricId } from "@/lib/types";

export type LeaderboardSectionId =
  | "performance"
  | "finishing"
  | "striking"
  | "grappling"
  | "durability";

export interface LeaderboardMetricConfig {
  title: string;
  description: string;
  metricLabel: string;
  category: LeaderboardSectionId;
}

export const STAT_LEADERBOARD_CONFIG: Record<
  LeaderboardMetricId,
  LeaderboardMetricConfig
> = {
  win_pct: {
    title: "Win Percentage",
    description: "Share of recorded UFC fights resulting in a win.",
    metricLabel: "Win %",
    category: "performance",
  },
  finish_rate_pct: {
    title: "Finish Rate",
    description: "Percentage of wins that ended via KO/TKO or submission.",
    metricLabel: "Finish %",
    category: "performance",
  },
  avg_knockdowns: {
    title: "Knockdown Average",
    description: "Average knockdowns landed per fight.",
    metricLabel: "KD Avg",
    category: "finishing",
  },
  avg_submissions: {
    title: "Submission Attempts",
    description: "Average submission attempts per fight.",
    metricLabel: "Subs / Fight",
    category: "finishing",
  },
  total_submissions: {
    title: "Career Submission Attempts",
    description: "Total recorded submission attempts.",
    metricLabel: "Total Subs",
    category: "finishing",
  },
  sig_strikes_landed_per_min: {
    title: "Significant Strikes Landed",
    description: "Significant strikes landed per minute (SLpM).",
    metricLabel: "SLpM",
    category: "striking",
  },
  sig_strikes_absorbed_per_min: {
    title: "Significant Strikes Absorbed",
    description: "Significant strikes absorbed per minute (SApM).",
    metricLabel: "SApM",
    category: "striking",
  },
  sig_strikes_accuracy_pct: {
    title: "Significant Strike Accuracy",
    description: "Percentage of significant strikes that land.",
    metricLabel: "Accuracy %",
    category: "striking",
  },
  sig_strikes_defense_pct: {
    title: "Significant Strike Defense",
    description: "Percentage of significant strikes defended.",
    metricLabel: "Defense %",
    category: "striking",
  },
  total_strikes_landed_avg: {
    title: "Total Strikes Landed",
    description: "Average total strikes landed per fight.",
    metricLabel: "Strikes",
    category: "striking",
  },
  takedowns_avg: {
    title: "Takedown Volume",
    description: "Average takedowns completed per fight.",
    metricLabel: "TD Avg",
    category: "grappling",
  },
  takedown_accuracy_pct: {
    title: "Takedown Accuracy",
    description: "Percentage of attempted takedowns completed.",
    metricLabel: "Accuracy %",
    category: "grappling",
  },
  takedown_defense_pct: {
    title: "Takedown Defense",
    description: "Percentage of opponent takedowns successfully defended.",
    metricLabel: "Defense %",
    category: "grappling",
  },
  avg_fight_duration_minutes: {
    title: "Average Fight Duration",
    description: "Average length of UFC bouts in minutes.",
    metricLabel: "Minutes",
    category: "durability",
  },
  time_in_cage_minutes: {
    title: "Time in Cage",
    description: "Total time spent fighting in the UFC Octagon (minutes).",
    metricLabel: "Minutes",
    category: "durability",
  },
};

export interface LeaderboardSectionConfig {
  id: LeaderboardSectionId;
  title: string;
  description: string;
  metrics: LeaderboardMetricId[];
}

export const STAT_LEADERBOARD_SECTIONS: LeaderboardSectionConfig[] = [
  {
    id: "performance",
    title: "Core Performance",
    description: "High-level efficiency metrics that summarise success.",
    metrics: ["win_pct", "finish_rate_pct"],
  },
  {
    id: "finishing",
    title: "Finishing & Excitement",
    description: "Aggression metrics showcasing fight-ending tendencies.",
    metrics: ["avg_knockdowns", "avg_submissions", "total_submissions"],
  },
  {
    id: "striking",
    title: "Striking Volume & Efficiency",
    description: "Significant strike pace, accuracy, and defence.",
    metrics: [
      "sig_strikes_landed_per_min",
      "sig_strikes_absorbed_per_min",
      "sig_strikes_accuracy_pct",
      "sig_strikes_defense_pct",
      "total_strikes_landed_avg",
    ],
  },
  {
    id: "grappling",
    title: "Grappling & Control",
    description: "Takedown output, accuracy, and defensive prowess.",
    metrics: ["takedowns_avg", "takedown_accuracy_pct", "takedown_defense_pct"],
  },
  {
    id: "durability",
    title: "Durability & Time in Cage",
    description: "Who spends the most time competing inside the Octagon.",
    metrics: ["avg_fight_duration_minutes", "time_in_cage_minutes"],
  },
];

export const DEFAULT_STATS_LEADERBOARD_METRICS: LeaderboardMetricId[] =
  STAT_LEADERBOARD_SECTIONS.flatMap((section) => section.metrics);
