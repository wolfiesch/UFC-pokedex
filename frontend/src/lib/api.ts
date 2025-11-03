import type {
  FighterComparisonEntry,
  FighterComparisonResponse,
  FighterListItem,
  PaginatedFightersResponse,
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

function normalizeFighterListItemPayload(item: unknown): FighterListItem | null {
  if (!isRecord(item)) {
    return null;
  }
  const fighterId = typeof item.fighter_id === "string" ? item.fighter_id : null;
  const detailUrl = typeof item.detail_url === "string" ? item.detail_url : null;
  const name = typeof item.name === "string" ? item.name : null;
  if (!fighterId || !detailUrl || !name) {
    return null;
  }
  return {
    fighter_id: fighterId,
    detail_url: detailUrl,
    name,
    nickname: typeof item.nickname === "string" ? item.nickname : null,
    division: typeof item.division === "string" ? item.division : null,
    height: typeof item.height === "string" ? item.height : null,
    weight: typeof item.weight === "string" ? item.weight : null,
    reach: typeof item.reach === "string" ? item.reach : null,
    stance: typeof item.stance === "string" ? item.stance : null,
    dob: typeof item.dob === "string" ? item.dob : null,
  };
}

function normalizePaginatedFightersResponse(
  payload: unknown,
  fallbackLimit: number,
  fallbackOffset: number
): PaginatedFightersResponse {
  if (!isRecord(payload)) {
    return {
      fighters: [],
      total: 0,
      limit: fallbackLimit,
      offset: fallbackOffset,
      has_more: false,
    };
  }

  const fightersSource = Array.isArray(payload.fighters) ? payload.fighters : [];
  const fighters = fightersSource
    .map((item) => normalizeFighterListItemPayload(item))
    .filter((item): item is FighterListItem => item !== null);

  const total = typeof payload.total === "number" ? payload.total : fighters.length;
  const limit = typeof payload.limit === "number" ? payload.limit : fallbackLimit;
  const offset = typeof payload.offset === "number" ? payload.offset : fallbackOffset;
  const hasMore =
    typeof payload.has_more === "boolean"
      ? payload.has_more
      : offset + fighters.length < total;

  return {
    fighters,
    total,
    limit,
    offset,
    has_more: hasMore,
  };
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
      .filter((entry): entry is [string, number] => typeof entry[1] === "number")
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
  const leaderboards = leaderboardsSource.reduce<LeaderboardDefinition[]>((acc, item, index) => {
    if (!isRecord(item)) {
      return acc;
    }
    const entriesSource = Array.isArray(item.entries) ? item.entries : [];
    const entries = entriesSource
      .map((entry, entryIndex) => normalizeLeaderboardEntry(entry, entryIndex))
      .filter((entryItem): entryItem is LeaderboardEntry => entryItem !== null);
    const metricId = typeof item.metric_id === "string" ? item.metric_id : `metric-${index}`;
    const title = typeof item.title === "string" ? item.title : toTitleCase(metricId);
    const description = typeof item.description === "string" ? item.description : undefined;

    acc.push({
      metric_id: metricId,
      title,
      description,
      entries,
    });

    return acc;
  }, []);

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
  const trends = trendsSource.reduce<TrendSeries[]>((acc, series, index) => {
    if (!isRecord(series)) {
      return acc;
    }
    const metricId = typeof series.metric_id === "string" ? series.metric_id : `trend-${index}`;
    const label = typeof series.label === "string" ? series.label : toTitleCase(metricId);
    const fighterId = typeof series.fighter_id === "string" ? series.fighter_id : undefined;
    const pointsSource = Array.isArray(series.points) ? series.points : [];
    const points = pointsSource
      .map((point) => normalizeTrendPoint(point))
      .filter((point): point is TrendPoint => point !== null);

    acc.push({
      metric_id: metricId,
      fighter_id: fighterId,
      label,
      points,
    });
    return acc;
  }, []);

  return { trends, generated_at: generatedAt };
}

function normalizeStatsCategory(
  category: unknown
): Record<string, string | number> {
  if (!isRecord(category)) {
    return {};
  }
  const stats: Record<string, string | number> = {};
  for (const [key, value] of Object.entries(category)) {
    if (typeof value === "string" || typeof value === "number") {
      stats[key] = value;
    }
  }
  return stats;
}

function normalizeComparisonEntry(entry: unknown): FighterComparisonEntry | null {
  if (!isRecord(entry) || typeof entry.fighter_id !== "string" || typeof entry.name !== "string") {
    return null;
  }

  return {
    fighter_id: entry.fighter_id,
    name: entry.name,
    record: typeof entry.record === "string" ? entry.record : null,
    division: typeof entry.division === "string" ? entry.division : null,
    striking: normalizeStatsCategory(entry.striking),
    grappling: normalizeStatsCategory(entry.grappling),
    significant_strikes: normalizeStatsCategory(entry.significant_strikes),
    takedown_stats: normalizeStatsCategory(entry.takedown_stats),
    career: normalizeStatsCategory(entry.career),
  };
}

export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
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
  const payload = await response.json();
  return normalizePaginatedFightersResponse(payload, limit, offset);
}

export async function searchFighters(
  query: string,
  stance: string | null = null,
  limit = 20,
  offset = 0
): Promise<PaginatedFightersResponse> {
  const trimmed = query.trim();
  const apiUrl = getApiBaseUrl();
  const params = new URLSearchParams();
  if (trimmed.length > 0) {
    params.set("q", trimmed);
  }
  if (stance && stance.length > 0) {
    params.set("stance", stance);
  }
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  const response = await fetch(`${apiUrl}/search/?${params.toString()}`, buildRequestInit());
  if (!response.ok) {
    throw new Error("Failed to search fighters");
  }
  const payload = await response.json();
  return normalizePaginatedFightersResponse(payload, limit, offset);
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

export async function compareFighters(
  fighterIds: string[]
): Promise<FighterComparisonResponse> {
  if (fighterIds.length < 2) {
    throw new Error("Select at least two fighters to compare.");
  }

  const apiUrl = getApiBaseUrl();
  const params = new URLSearchParams();
  fighterIds.forEach((id) => {
    if (id) {
      params.append("fighter_ids", id);
    }
  });

  const response = await fetch(
    `${apiUrl}/fighters/compare?${params.toString()}`,
    buildRequestInit()
  );
  if (!response.ok) {
    throw new Error("Failed to fetch fighter comparison data");
  }

  const payload = await response.json();
  if (!isRecord(payload)) {
    return { fighters: [] };
  }

  const fightersSource = Array.isArray(payload.fighters) ? payload.fighters : [];
  const fighters = fightersSource
    .map((entry) => normalizeComparisonEntry(entry))
    .filter((entry): entry is FighterComparisonEntry => entry !== null);

  return { fighters };
}
