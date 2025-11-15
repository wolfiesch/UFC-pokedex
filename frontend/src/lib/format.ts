const METRIC_LABEL_OVERRIDES: Record<string, string> = {
  win_pct: "Win Percentage",
  finish_rate_pct: "Finish Rate (%)",
  sig_strikes_landed_per_min: "Sig. Strikes Landed / Min",
  sig_strikes_absorbed_per_min: "Sig. Strikes Absorbed / Min",
  sig_strikes_accuracy_pct: "Sig. Strike Accuracy (%)",
  sig_strikes_defense_pct: "Sig. Strike Defense (%)",
  sig_strikes_landed_total: "Total Sig. Strikes Landed",
  sig_strikes_absorbed_total: "Total Sig. Strikes Absorbed",
  sig_strikes_landed_avg: "Avg. Sig. Strikes Landed",
  total_strikes_landed_avg: "Avg. Total Strikes Landed",
  total_strikes_landed_total: "Total Strikes Landed",
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
  time_in_cage_minutes: "Time in Cage (min)",
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

const CACHE_LIMIT = 256;
const TITLE_CASE_CACHE = new Map<string, string>();
const METRIC_LABEL_CACHE = new Map<string, string>();
const CATEGORY_LABEL_CACHE = new Map<string, string>();

function cacheWithLimit(map: Map<string, string>, key: string, value: string) {
  if (map.size >= CACHE_LIMIT) {
    const oldestKey = map.keys().next().value;
    map.delete(oldestKey);
  }
  map.set(key, value);
}

function toTitleCase(value: string): string {
  const normalized = value ?? "";
  const cached = TITLE_CASE_CACHE.get(normalized);
  if (cached) {
    return cached;
  }

  const computed = normalized
    .split(/[_\-]+/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");

  cacheWithLimit(TITLE_CASE_CACHE, normalized, computed);
  return computed;
}

export function formatMetricLabel(metricKey: string): string {
  const cached = METRIC_LABEL_CACHE.get(metricKey);
  if (cached) {
    return cached;
  }

  const label = METRIC_LABEL_OVERRIDES[metricKey] ?? toTitleCase(metricKey);
  cacheWithLimit(METRIC_LABEL_CACHE, metricKey, label);
  return label;
}

export function formatCategoryLabel(categoryKey: string): string {
  const cached = CATEGORY_LABEL_CACHE.get(categoryKey);
  if (cached) {
    return cached;
  }

  const label =
    CATEGORY_LABEL_OVERRIDES[categoryKey] ?? toTitleCase(categoryKey);
  cacheWithLimit(CATEGORY_LABEL_CACHE, categoryKey, label);
  return label;
}
