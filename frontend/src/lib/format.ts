const METRIC_LABEL_OVERRIDES: Record<string, string> = {
  sig_strikes_landed_per_min: "Sig. Strikes Landed / Min",
  sig_strikes_absorbed_per_min: "Sig. Strikes Absorbed / Min",
  sig_strikes_accuracy_pct: "Sig. Strike Accuracy (%)",
  sig_strikes_defense_pct: "Sig. Strike Defense (%)",
  sig_strikes_landed_avg: "Avg. Sig. Strikes Landed",
  total_strikes_landed_avg: "Avg. Total Strikes Landed",
  avg_knockdowns: "Avg. Knockdowns",
  takedowns_completed_avg: "Avg. Takedowns Landed",
  takedown_accuracy_pct: "Takedown Accuracy (%)",
  takedown_defense_pct: "Takedown Defense (%)",
  takedowns_avg: "Avg. Takedowns",
  avg_submissions: "Avg. Submission Attempts",
  total_submissions: "Total Submissions",
  avg_fight_duration_seconds: "Avg. Fight Duration (s)",
  longest_win_streak: "Longest Win Streak",
  avg_fight_duration_minutes: "Avg. Fight Duration (min)",
  avg_submission_attempts: "Avg. Submission Attempts",
  avg_sig_strikes_accuracy_pct: "Avg. Sig. Strike Accuracy (%)",
  avg_takedown_accuracy_pct: "Avg. Takedown Accuracy (%)",
};

const CATEGORY_LABEL_OVERRIDES: Record<string, string> = {
  striking: "Striking",
  grappling: "Grappling",
  significant_strikes: "Significant Strikes",
  takedown_stats: "Takedowns",
  career: "Career Overview",
};

function toTitleCase(value: string): string {
  return value
    .split(/[_\-]+/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

export function formatMetricLabel(metricKey: string): string {
  return METRIC_LABEL_OVERRIDES[metricKey] ?? toTitleCase(metricKey);
}

export function formatCategoryLabel(categoryKey: string): string {
  return CATEGORY_LABEL_OVERRIDES[categoryKey] ?? toTitleCase(categoryKey);
}
