import type {
  FighterListItem,
  LeaderboardDefinition,
  LeaderboardEntry,
  StatsLeaderboardsResponse,
  StatsSummaryMetric,
  StatsSummaryResponse,
  StatsTrendsResponse,
  TrendPoint,
  TrendSeries,
} from "./types";

const REQUEST_OPTIONS: RequestInit = { cache: "no-store" };

function buildRequestInit(init?: RequestInit): RequestInit {
  return { ...REQUEST_OPTIONS, ...init };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function toTitleCase(id: string): string {
  return id
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (segment) => segment.toUpperCase())
    .trim();
}

function normalizeSummaryMetric(metric: unknown): StatsSummaryMetric | null {
  if (!isRecord(metric) || typeof metric.id !== "string") {
    return null;
  }
  const rawValue = metric.value;
  if (typeof rawValue !== "number") {
    return null;
  }
  return {
    id: metric.id,
    label: typeof metric.label === "string" ? metric.label : toTitleCase(metric.id),
    value: rawValue,
    description: typeof metric.description === "string" ? metric.description : undefined,
  };
}

function normalizeStatsSummary(payload: unknown): StatsSummaryResponse {
  if (isRecord(payload)) {
    const generatedAt = typeof payload.generated_at === "string" ? payload.generated_at : undefined;
    if (Array.isArray(payload.metrics)) {
      const metrics = payload.metrics
        .map((item) => normalizeSummaryMetric(item))
        .filter((item): item is StatsSummaryMetric => item !== null);
      return { metrics, generated_at: generatedAt };
    }
    const derivedMetrics: StatsSummaryMetric[] = Object.entries(payload)
      .filter(([, value]) => typeof value === "number")
      .map(([key, value]) => ({
        id: key,
        label: toTitleCase(key),
        value,
      }));
    return { metrics: derivedMetrics, generated_at: generatedAt };
  }
  return { metrics: [] };
}

function normalizeLeaderboardEntry(
  entry: unknown,
  index: number
): LeaderboardEntry | null {
  if (!isRecord(entry)) {
    return null;
  }
  const fighterId = typeof entry.fighter_id === "string" ? entry.fighter_id : `unknown-${index}`;
  const fighterName = typeof entry.fighter_name === "string" ? entry.fighter_name : "Unknown";
  const metricValue = typeof entry.metric_value === "number" ? entry.metric_value : Number(entry.value ?? 0);
  if (Number.isNaN(metricValue)) {
    return null;
  }
  const detailUrl = typeof entry.detail_url === "string" ? entry.detail_url : undefined;
  return {
    fighter_id: fighterId,
    fighter_name: fighterName,
    metric_value: metricValue,
    detail_url: detailUrl,
  };
}

function normalizeLeaderboards(payload: unknown): StatsLeaderboardsResponse {
  if (!isRecord(payload)) {
    return { leaderboards: [] };
  }
  const generatedAt = typeof payload.generated_at === "string" ? payload.generated_at : undefined;
  const leaderboardsSource = Array.isArray(payload.leaderboards) ? payload.leaderboards : [];
  const leaderboards: LeaderboardDefinition[] = leaderboardsSource
    .map((item, index) => {
      if (!isRecord(item)) {
        return null;
      }
      const entriesSource = Array.isArray(item.entries) ? item.entries : [];
      const entries = entriesSource
        .map((entry, entryIndex) => normalizeLeaderboardEntry(entry, entryIndex))
        .filter((entryItem): entryItem is LeaderboardEntry => entryItem !== null);
      const metricId = typeof item.metric_id === "string" ? item.metric_id : `metric-${index}`;
      const title = typeof item.title === "string" ? item.title : toTitleCase(metricId);
      const description = typeof item.description === "string" ? item.description : undefined;
      return {
        metric_id: metricId,
        title,
        description,
        entries,
      };
    })
    .filter((leaderboard): leaderboard is LeaderboardDefinition => leaderboard !== null);

  return { leaderboards, generated_at: generatedAt };
}

function normalizeTrendPoint(point: unknown): TrendPoint | null {
  if (!isRecord(point) || typeof point.timestamp !== "string") {
    return null;
  }
  const value = typeof point.value === "number" ? point.value : Number(point.value ?? NaN);
  if (Number.isNaN(value)) {
    return null;
  }
  return {
    timestamp: point.timestamp,
    value,
  };
}

function normalizeTrends(payload: unknown): StatsTrendsResponse {
  if (!isRecord(payload)) {
    return { trends: [] };
  }
  const generatedAt = typeof payload.generated_at === "string" ? payload.generated_at : undefined;
  const trendsSource = Array.isArray(payload.trends) ? payload.trends : [];
  const trends: TrendSeries[] = trendsSource
    .map((series, index) => {
      if (!isRecord(series)) {
        return null;
      }
      const metricId = typeof series.metric_id === "string" ? series.metric_id : `trend-${index}`;
      const label = typeof series.label === "string" ? series.label : toTitleCase(metricId);
      const fighterId = typeof series.fighter_id === "string" ? series.fighter_id : undefined;
      const pointsSource = Array.isArray(series.points) ? series.points : [];
      const points = pointsSource
        .map((point) => normalizeTrendPoint(point))
        .filter((point): point is TrendPoint => point !== null);
      return {
        metric_id: metricId,
        fighter_id: fighterId,
        label,
        points,
      };
    })
    .filter((series): series is TrendSeries => series !== null);

  return { trends, generated_at: generatedAt };
}

export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

export interface PaginatedFightersResponse {
  fighters: FighterListItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export async function getFighters(
  limit = 20,
  offset = 0
): Promise<PaginatedFightersResponse> {
  const apiUrl = getApiBaseUrl();
  const response = await fetch(
    `${apiUrl}/fighters/?limit=${limit}&offset=${offset}`,
    buildRequestInit()
  );
  if (!response.ok) {
    throw new Error("Failed to fetch fighters");
  }
  return response.json();
}

export async function getRandomFighter(): Promise<FighterListItem> {
  const apiUrl = getApiBaseUrl();
  const response = await fetch(`${apiUrl}/fighters/random`, buildRequestInit());
  if (!response.ok) {
    throw new Error("Failed to fetch random fighter");
  }
  return response.json();
}

/**
 * Retrieve global KPI metrics summarising the state of the UFC data corpus. The
 * response is normalised into a structured array for predictable rendering
 * within dashboard-style cards.
 */
export async function getStatsSummary(init?: RequestInit): Promise<StatsSummaryResponse> {
  const apiUrl = getApiBaseUrl();
  const response = await fetch(`${apiUrl}/stats/summary`, buildRequestInit(init));
  if (!response.ok) {
    throw new Error("Failed to fetch stats summary");
  }
  const payload = await response.json();
  return normalizeStatsSummary(payload);
}

/**
 * Fetch ranked fighter leaderboards keyed by a set of metrics (wins, finishes,
 * streaks, etc.). Each leaderboard is normalised to ensure fallback values are
 * available even when optional fields are omitted by the backend.
 */
export async function getStatsLeaderboards(
  init?: RequestInit
): Promise<StatsLeaderboardsResponse> {
  const apiUrl = getApiBaseUrl();
  const response = await fetch(`${apiUrl}/stats/leaderboards`, buildRequestInit(init));
  if (!response.ok) {
    throw new Error("Failed to fetch stats leaderboards");
  }
  const payload = await response.json();
  return normalizeLeaderboards(payload);
}

/**
 * Load aggregated time-series data illustrating how key metrics evolve. The
 * resulting structure is ready for consumption by charting libraries and
 * includes defensive defaults when optional metadata is absent.
 */
export async function getStatsTrends(init?: RequestInit): Promise<StatsTrendsResponse> {
  const apiUrl = getApiBaseUrl();
  const response = await fetch(`${apiUrl}/stats/trends`, buildRequestInit(init));
  if (!response.ok) {
    throw new Error("Failed to fetch stats trends");
  }
  const payload = await response.json();
  return normalizeTrends(payload);
}
