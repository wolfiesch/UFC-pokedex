import type {
  FavoriteActivityItem,
  FavoriteCollectionCreatePayload,
  FavoriteCollectionDetail,
  FavoriteCollectionListResponse,
  FavoriteCollectionStats,
  FavoriteCollectionSummary,
  FavoriteCollectionUpdatePayload,
  FavoriteEntry,
  FavoriteEntryCreatePayload,
  FavoriteEntryReorderPayload,
  FavoriteEntryUpdatePayload,
  FavoriteUpcomingFight,
  FightGraphLink,
  FightGraphNode,
  FightGraphQueryParams,
  FightGraphResponse,
  FighterComparisonEntry,
  FighterComparisonResponse,
  FighterDetail,
  FighterListItem,
  FightHistoryEntry,
  LeaderboardDefinition,
  LeaderboardEntry,
  PaginatedFightersResponse,
  StatsLeaderboardsResponse,
  StatsSummaryMetric,
  StatsSummaryResponse,
  StatsTrendsResponse,
  TrendPoint,
  TrendSeries,
} from "./types";
import { ApiError, ErrorResponseData, NotFoundError } from "./errors";
import { logger } from "./logger";

const REQUEST_OPTIONS: RequestInit = { cache: "no-store" };
const DEFAULT_TIMEOUT_MS = 30000; // 30 seconds
const MAX_RETRY_ATTEMPTS = 3;
const RETRY_DELAY_MS = 1000; // 1 second base delay

/**
 * Sleep for a specified duration (for retry delays)
 */
async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Calculate exponential backoff delay
 */
function getRetryDelay(retryCount: number, baseDelay = RETRY_DELAY_MS): number {
  return baseDelay * Math.pow(2, retryCount - 1);
}

/**
 * Fetch with timeout support
 */
async function fetchWithTimeout(
  url: string,
  init?: RequestInit,
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...init,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === "AbortError") {
      throw ApiError.fromTimeout(timeoutMs);
    }
    throw error;
  }
}

/**
 * Parse error response from backend
 */
async function parseErrorResponse(
  response: Response
): Promise<ApiError> {
  const requestId = response.headers.get("X-Request-ID") || undefined;

  try {
    const data: ErrorResponseData = await response.json();
    return ApiError.fromResponse(data, response.status);
  } catch {
    // If we can't parse the error response, create a generic error
    return new ApiError(
      response.statusText || "Request failed",
      {
        statusCode: response.status,
        detail: `HTTP ${response.status} error occurred`,
        requestId,
      }
    );
  }
}

/**
 * Fetch with retry logic for retryable errors
 */
async function fetchWithRetry(
  url: string,
  init?: RequestInit,
  options: {
    timeoutMs?: number;
    maxRetries?: number;
    retryDelay?: number;
  } = {}
): Promise<Response> {
  const {
    timeoutMs = DEFAULT_TIMEOUT_MS,
    maxRetries = MAX_RETRY_ATTEMPTS,
    retryDelay = RETRY_DELAY_MS,
  } = options;

  let lastError: ApiError | null = null;
  const method = init?.method || "GET";

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const startTime = Date.now();

      if (attempt > 0) {
        const delay = getRetryDelay(attempt, retryDelay);
        logger.logRetry(method, url, attempt, maxRetries);
        await sleep(delay);
      }

      logger.logRequest(method, url, { attempt });

      const response = await fetchWithTimeout(url, init, timeoutMs);
      const duration = Date.now() - startTime;

      logger.logResponse(method, url, response.status, duration);

      if (!response.ok) {
        let error = await parseErrorResponse(response);

        // Create new error with retry count (readonly property)
        if (attempt > 0) {
          error = new ApiError(error.message, {
            errorType: error.errorType,
            statusCode: error.statusCode,
            detail: error.detail,
            timestamp: error.timestamp,
            requestId: error.requestId,
            path: error.path,
            retryAfter: error.retryAfter,
            validationErrors: error.validationErrors,
            retryCount: attempt,
          });
        }

        // Don't retry if error is not retryable
        if (!error.isRetryable || attempt === maxRetries) {
          logger.logApiError(method, url, error);
          throw error;
        }

        lastError = error;
        continue;
      }

      return response;
    } catch (error) {
      if (error instanceof ApiError) {
        lastError = error;

        // Don't retry if error is not retryable
        if (!error.isRetryable || attempt === maxRetries) {
          logger.logApiError(method, url, error);
          throw error;
        }
      } else if (error instanceof Error) {
        // Network error or other fetch error
        lastError = ApiError.fromNetworkError(error, attempt);

        if (attempt === maxRetries) {
          logger.logApiError(method, url, lastError);
          throw lastError;
        }
      } else {
        // Unknown error type
        const unknownError = new ApiError("Unknown error occurred", {
          detail: String(error),
          retryCount: attempt,
        });
        logger.logApiError(method, url, unknownError);
        throw unknownError;
      }
    }
  }

  // This should never be reached, but TypeScript needs it
  throw lastError || new ApiError("Request failed after retries");
}

function buildRequestInit(init?: RequestInit): RequestInit {
  return { ...REQUEST_OPTIONS, ...init };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function toFiniteNumber(value: unknown, fallback = 0): number {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : fallback;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isNaN(parsed) ? fallback : parsed;
  }
  return fallback;
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
    image_url: typeof item.image_url === "string" ? item.image_url : null,
    age:
      typeof item.age === "number" && Number.isFinite(item.age)
        ? item.age
        : null,
    current_streak_type:
      typeof item.current_streak_type === "string"
        ? (item.current_streak_type as FighterListItem["current_streak_type"])
        : "none",
    current_streak_count:
      typeof item.current_streak_count === "number"
        ? item.current_streak_count
        : 0,
  };
}

function normalizeFavoriteActivityItem(value: unknown): FavoriteActivityItem | null {
  if (!isRecord(value)) {
    return null;
  }
  const entryId = toFiniteNumber(value.entry_id, NaN);
  const fighterId = typeof value.fighter_id === "string" ? value.fighter_id : "";
  const action = typeof value.action === "string" ? value.action : "";
  const occurredAt =
    typeof value.occurred_at === "string" ? value.occurred_at : new Date(0).toISOString();
  if (!Number.isFinite(entryId) || !fighterId || !action) {
    return null;
  }
  const metadata = isRecord(value.metadata) ? value.metadata : {};
  return {
    entry_id: entryId,
    fighter_id: fighterId,
    action,
    occurred_at: occurredAt,
    metadata,
  };
}

function normalizeFavoriteUpcomingFight(value: unknown): FavoriteUpcomingFight | null {
  if (!isRecord(value)) {
    return null;
  }
  const fighterId = typeof value.fighter_id === "string" ? value.fighter_id : "";
  const opponentName = typeof value.opponent_name === "string" ? value.opponent_name : "";
  const eventName = typeof value.event_name === "string" ? value.event_name : "";
  if (!fighterId || !opponentName || !eventName) {
    return null;
  }
  return {
    fighter_id: fighterId,
    opponent_name: opponentName,
    event_name: eventName,
    event_date: typeof value.event_date === "string" ? value.event_date : null,
    weight_class: typeof value.weight_class === "string" ? value.weight_class : null,
  };
}

function normalizeFavoriteCollectionStats(value: unknown): FavoriteCollectionStats {
  if (!isRecord(value)) {
    return {
      total_fighters: 0,
      win_rate: 0,
      result_breakdown: {},
      divisions: [],
      upcoming_fights: [],
    };
  }
  const divisions = Array.isArray(value.divisions)
    ? value.divisions.filter((division): division is string => typeof division === "string")
    : [];
  const breakdown = isRecord(value.result_breakdown)
    ? Object.fromEntries(
        Object.entries(value.result_breakdown).map(([key, raw]) => [
          key,
          toFiniteNumber(raw, 0),
        ])
      )
    : {};
  const upcomingSource = Array.isArray(value.upcoming_fights)
    ? value.upcoming_fights
    : [];
  const upcoming: FavoriteUpcomingFight[] = upcomingSource
    .map((entry) => normalizeFavoriteUpcomingFight(entry))
    .filter((entry): entry is FavoriteUpcomingFight => entry !== null);

  return {
    total_fighters: toFiniteNumber(value.total_fighters, 0),
    win_rate: toFiniteNumber(value.win_rate, 0),
    result_breakdown: breakdown,
    divisions,
    upcoming_fights: upcoming,
  };
}

function normalizeFavoriteEntry(value: unknown): FavoriteEntry | null {
  if (!isRecord(value)) {
    return null;
  }
  const id = toFiniteNumber(value.id, NaN);
  const fighterId = typeof value.fighter_id === "string" ? value.fighter_id : "";
  if (!Number.isFinite(id) || !fighterId) {
    return null;
  }
  const position = toFiniteNumber(value.position, 0);
  const tags = Array.isArray(value.tags)
    ? value.tags.filter((tag): tag is string => typeof tag === "string")
    : [];
  const metadata = isRecord(value.metadata)
    ? { ...value.metadata }
    : isRecord(value.metadata_json)
      ? { ...value.metadata_json }
      : {};
  const createdAt =
    typeof value.created_at === "string"
      ? value.created_at
      : new Date(0).toISOString();
  const addedAt =
    typeof value.added_at === "string" ? value.added_at : createdAt;
  const updatedAt =
    typeof value.updated_at === "string" ? value.updated_at : addedAt;
  const collectionIdRaw = value.collection_id ?? (isRecord(value.collection) ? value.collection.id : undefined);
  const collectionId = toFiniteNumber(collectionIdRaw, NaN);
  const fighterName =
    typeof value.fighter_name === "string" ? value.fighter_name : undefined;
  const fighterPayload = isRecord(value.fighter) ? value.fighter : null;
  const fighter = fighterPayload
    ? normalizeFighterListItemPayload(fighterPayload)
    : null;

  return {
    id,
    entry_id: id,
    fighter_id: fighterId,
    collection_id: Number.isFinite(collectionId) ? collectionId : undefined,
    fighter_name: fighterName,
    fighter,
    position,
    notes:
      typeof value.notes === "string"
        ? value.notes
        : value.notes === null
          ? null
          : undefined,
    tags,
    metadata,
    created_at: createdAt,
    updated_at: updatedAt,
    added_at: addedAt,
  };
}

function normalizeFavoriteCollectionSummary(
  value: unknown
): FavoriteCollectionSummary | null {
  if (!isRecord(value)) {
    return null;
  }
  const id = toFiniteNumber(value.id, NaN);
  const userId = typeof value.user_id === "string" ? value.user_id : "";
  const title = typeof value.title === "string" ? value.title : "";
  if (!Number.isFinite(id) || !userId || !title) {
    return null;
  }
  const stats = value.stats ? normalizeFavoriteCollectionStats(value.stats) : null;
  return {
    id,
    collection_id: id,
    user_id: userId,
    title,
    description:
      typeof value.description === "string"
        ? value.description
        : value.description === null
          ? null
          : undefined,
    is_public: Boolean(value.is_public),
    slug:
      typeof value.slug === "string"
        ? value.slug
        : value.slug === null
          ? null
          : undefined,
    metadata: isRecord(value.metadata) ? { ...value.metadata } : {},
    created_at:
      typeof value.created_at === "string" ? value.created_at : new Date(0).toISOString(),
    updated_at:
      typeof value.updated_at === "string" ? value.updated_at : new Date(0).toISOString(),
    stats,
  };
}

function normalizeFavoriteCollectionDetail(
  value: unknown
): FavoriteCollectionDetail | null {
  const summary = normalizeFavoriteCollectionSummary(value);
  if (!summary) {
    return null;
  }
  const source = isRecord(value) ? value : {};
  const entriesSource = Array.isArray(source.entries) ? source.entries : [];
  const activitySource = Array.isArray(source.activity) ? source.activity : [];

  const entries: FavoriteEntry[] = entriesSource
    .map((entry) => normalizeFavoriteEntry(entry))
    .filter((entry): entry is FavoriteEntry => entry !== null);
  const activity: FavoriteActivityItem[] = activitySource
    .map((item) => normalizeFavoriteActivityItem(item))
    .filter((item): item is FavoriteActivityItem => item !== null);

  const stats = normalizeFavoriteCollectionStats(source.stats);

  return {
    ...summary,
    entries,
    activity,
    stats,
  };
}

function normalizeFavoriteCollectionList(
  value: unknown
): FavoriteCollectionListResponse {
  if (!isRecord(value)) {
    return { total: 0, collections: [] };
  }
  const collectionsSource = Array.isArray(value.collections) ? value.collections : [];
  const collections = collectionsSource
    .map((entry) => normalizeFavoriteCollectionSummary(entry))
    .filter((entry): entry is FavoriteCollectionSummary => entry !== null);
  return {
    total: toFiniteNumber(value.total, collections.length),
    collections,
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

function normalizeMetricsRecord(
  source: unknown
): Record<string, string | number | null | undefined> {
  if (!isRecord(source)) {
    return {};
  }

  return Object.entries(source).reduce<Record<string, string | number | null | undefined>>(
    (accumulator, [rawKey, rawValue]) => {
      if (typeof rawKey !== "string" || rawKey.length === 0) {
        return accumulator;
      }
      if (
        typeof rawValue === "string" ||
        typeof rawValue === "number" ||
        rawValue === null ||
        rawValue === undefined
      ) {
        accumulator[rawKey] = rawValue ?? null;
        return accumulator;
      }

      if (typeof rawValue === "boolean") {
        accumulator[rawKey] = rawValue ? 1 : 0;
        return accumulator;
      }

      accumulator[rawKey] = null;
      return accumulator;
    },
    {}
  );
}

function normalizeFightHistoryEntryPayload(
  entry: unknown
): FightHistoryEntry | null {
  if (!isRecord(entry)) {
    return null;
  }

  const fightId = typeof entry.fight_id === "string" ? entry.fight_id : null;
  const eventName = typeof entry.event_name === "string" ? entry.event_name : null;
  const opponent = typeof entry.opponent === "string" ? entry.opponent : null;
  const result = typeof entry.result === "string" ? entry.result : null;
  const method = typeof entry.method === "string" ? entry.method : null;

  if (!fightId || !eventName || !opponent || !result || !method) {
    return null;
  }

  const round = typeof entry.round === "number" ? entry.round : null;
  const time = typeof entry.time === "string" ? entry.time : null;
  const eventDate = typeof entry.event_date === "string" ? entry.event_date : null;
  const opponentId = typeof entry.opponent_id === "string" ? entry.opponent_id : null;
  const fightCardUrl = typeof entry.fight_card_url === "string" ? entry.fight_card_url : null;
  const stats = normalizeMetricsRecord(entry.stats);

  return {
    fight_id: fightId,
    event_name: eventName,
    event_date: eventDate,
    opponent,
    opponent_id: opponentId,
    result,
    method,
    round,
    time,
    fight_card_url: fightCardUrl,
    stats,
  };
}

function normalizeFighterDetailPayload(payload: unknown): FighterDetail {
  const base = normalizeFighterListItemPayload(payload);

  if (!base) {
    throw new ApiError("Invalid fighter detail payload", {
      detail: "Missing fighter identifier or name",
    });
  }

  const payloadRecord = isRecord(payload) ? payload : {};
  const recordRaw = payloadRecord.record;
  const record = typeof recordRaw === "string" ? recordRaw : null;
  const legReachRaw = payloadRecord.leg_reach;
  const legReach = typeof legReachRaw === "string" ? legReachRaw : null;
  const ageRaw = payloadRecord.age;
  const age =
    typeof ageRaw === "number" && Number.isFinite(ageRaw) ? ageRaw : null;

  const striking = normalizeMetricsRecord(
    payloadRecord.striking
  );
  const grappling = normalizeMetricsRecord(
    payloadRecord.grappling
  );
  const significantStrikes = normalizeMetricsRecord(
    payloadRecord.significant_strikes
  );
  const takedownStats = normalizeMetricsRecord(
    payloadRecord.takedown_stats
  );
  const career = normalizeMetricsRecord(
    payloadRecord.career
  );

  const historySource = Array.isArray(payloadRecord.fight_history)
    ? (payloadRecord.fight_history as unknown[])
    : [];
  const fightHistory = historySource
    .map((entry) => normalizeFightHistoryEntryPayload(entry))
    .filter((entry): entry is FightHistoryEntry => entry !== null);

  return {
    ...base,
    record,
    leg_reach: legReach,
    age,
    striking,
    grappling,
    significant_strikes: significantStrikes,
    takedown_stats: takedownStats,
    career,
    fight_history: fightHistory,
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
    age:
      typeof entry.age === "number" && Number.isFinite(entry.age)
        ? entry.age
        : null,
    striking: normalizeStatsCategory(entry.striking),
    grappling: normalizeStatsCategory(entry.grappling),
    significant_strikes: normalizeStatsCategory(entry.significant_strikes),
    takedown_stats: normalizeStatsCategory(entry.takedown_stats),
    career: normalizeStatsCategory(entry.career),
  };
}

function normalizeFightGraphResultBreakdown(
  value: unknown
): FightGraphLink["result_breakdown"] {
  if (!isRecord(value)) {
    return {};
  }

  return Object.entries(value).reduce<FightGraphLink["result_breakdown"]>(
    (accumulator, [fighterId, breakdown]) => {
      if (!isRecord(breakdown)) {
        return accumulator;
      }

      const normalized: Record<string, number> = {};
      for (const [category, count] of Object.entries(breakdown)) {
        const parsed = toFiniteNumber(count, Number.NaN);
        if (Number.isFinite(parsed)) {
          normalized[category] = parsed;
        }
      }

      if (Object.keys(normalized).length > 0) {
        accumulator[fighterId] = normalized;
      }

      return accumulator;
    },
    {}
  );
}

function normalizeFightGraphNode(node: unknown): FightGraphNode | null {
  if (!isRecord(node) || typeof node.fighter_id !== "string" || typeof node.name !== "string") {
    return null;
  }

  const totalFights = toFiniteNumber(node.total_fights, 0);
  const latestEventDate =
    typeof node.latest_event_date === "string"
      ? node.latest_event_date
      : node.latest_event_date instanceof Date
        ? node.latest_event_date.toISOString()
        : null;

  return {
    fighter_id: node.fighter_id,
    name: node.name,
    division: typeof node.division === "string" ? node.division : null,
    record: typeof node.record === "string" ? node.record : null,
    image_url: typeof node.image_url === "string" ? node.image_url : null,
    total_fights: Number.isFinite(totalFights) ? totalFights : 0,
    latest_event_date: latestEventDate,
  };
}

function normalizeFightGraphLink(link: unknown): FightGraphLink | null {
  if (!isRecord(link) || typeof link.source !== "string" || typeof link.target !== "string") {
    return null;
  }

  const fights = toFiniteNumber(link.fights, 0);
  const firstEventDate =
    typeof link.first_event_date === "string"
      ? link.first_event_date
      : link.first_event_date instanceof Date
        ? link.first_event_date.toISOString()
        : null;
  const lastEventDate =
    typeof link.last_event_date === "string"
      ? link.last_event_date
      : link.last_event_date instanceof Date
        ? link.last_event_date.toISOString()
        : null;

  return {
    source: link.source,
    target: link.target,
    fights: Number.isFinite(fights) ? fights : 0,
    first_event_name:
      typeof link.first_event_name === "string" ? link.first_event_name : null,
    first_event_date: firstEventDate,
    last_event_name: typeof link.last_event_name === "string" ? link.last_event_name : null,
    last_event_date: lastEventDate,
    result_breakdown: normalizeFightGraphResultBreakdown(link.result_breakdown),
  };
}

function normalizeFightGraphResponse(payload: unknown): FightGraphResponse {
  if (!isRecord(payload)) {
    return { nodes: [], links: [], metadata: {} };
  }

  const nodesSource = Array.isArray(payload.nodes) ? payload.nodes : [];
  const nodes = nodesSource
    .map((node) => normalizeFightGraphNode(node))
    .filter((node): node is FightGraphNode => node !== null);

  const linksSource = Array.isArray(payload.links) ? payload.links : [];
  const links = linksSource
    .map((link) => normalizeFightGraphLink(link))
    .filter((link): link is FightGraphLink => link !== null);

  const metadata = isRecord(payload.metadata) ? { ...payload.metadata } : {};

  return { nodes, links, metadata };
}

export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

export async function getFighters(
  limit = 20,
  offset = 0
): Promise<PaginatedFightersResponse> {
  const apiUrl = getApiBaseUrl();
  try {
    const response = await fetchWithRetry(
      `${apiUrl}/fighters/?limit=${limit}&offset=${offset}&include_streak=1&streak_window=6`,
      buildRequestInit()
    );
    const payload = await response.json();
    return normalizePaginatedFightersResponse(payload, limit, offset);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === "SyntaxError") {
      throw ApiError.fromParseError(error);
    }
    throw ApiError.fromNetworkError(
      error instanceof Error ? error : new Error(String(error))
    );
  }
}

export async function searchFighters(
  query: string,
  stance: string | null = null,
  division: string | null = null,
  championStatusFilters: string[] = [],
  streakType: "win" | "loss" | null = null,
  minStreakCount: number | null = null,
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
  if (division && division.length > 0) {
    params.set("division", division);
  }
  // Add champion status filters (supports multiple values)
  championStatusFilters.forEach((status) => {
    if (status && status.length > 0) {
      params.append("champion_statuses", status);
    }
  });
  // Add streak filters if both type and count are provided
  if (streakType && minStreakCount !== null && minStreakCount > 0) {
    params.set("streak_type", streakType);
    params.set("min_streak_count", String(minStreakCount));
  }
  params.set("limit", String(limit));
  params.set("offset", String(offset));

  try {
    const response = await fetchWithRetry(
      `${apiUrl}/search/?${params.toString()}`,
      buildRequestInit()
    );
    const payload = await response.json();
    return normalizePaginatedFightersResponse(payload, limit, offset);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === "SyntaxError") {
      throw ApiError.fromParseError(error);
    }
    throw ApiError.fromNetworkError(
      error instanceof Error ? error : new Error(String(error))
    );
  }
}

export async function getRandomFighter(): Promise<FighterListItem> {
  const apiUrl = getApiBaseUrl();
  try {
    const response = await fetchWithRetry(
      `${apiUrl}/fighters/random`,
      buildRequestInit()
    );
    return response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw ApiError.fromNetworkError(
      error instanceof Error ? error : new Error(String(error))
    );
  }
}

export async function getFighter(fighterId: string): Promise<FighterDetail> {
  const apiUrl = getApiBaseUrl();
  try {
    const response = await fetchWithRetry(
      `${apiUrl}/fighters/${fighterId}`,
      buildRequestInit()
    );

    const payload = await response.json();
    return normalizeFighterDetailPayload(payload);
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.statusCode === 404) {
        throw new NotFoundError(
          "Fighter",
          `Fighter with ID "${fighterId}" not found`
        );
      }
      throw error;
    }

    if (error instanceof Error && error.name === "SyntaxError") {
      throw ApiError.fromParseError(error);
    }

    throw ApiError.fromNetworkError(
      error instanceof Error ? error : new Error(String(error))
    );
  }
}

/**
 * Retrieve global KPI metrics summarising the state of the UFC data corpus. The
 * response is normalised into a structured array for predictable rendering
 * within dashboard-style cards.
 */
export async function getStatsSummary(init?: RequestInit): Promise<StatsSummaryResponse> {
  const apiUrl = getApiBaseUrl();
  try {
    const response = await fetchWithRetry(
      `${apiUrl}/stats/summary`,
      buildRequestInit(init)
    );
    const payload = await response.json();
    return normalizeStatsSummary(payload);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw ApiError.fromNetworkError(
      error instanceof Error ? error : new Error(String(error))
    );
  }
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
  try {
    const response = await fetchWithRetry(
      `${apiUrl}/stats/leaderboards`,
      buildRequestInit(init)
    );
    const payload = await response.json();
    return normalizeLeaderboards(payload);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw ApiError.fromNetworkError(
      error instanceof Error ? error : new Error(String(error))
    );
  }
}

/**
 * Load aggregated time-series data illustrating how key metrics evolve. The
 * resulting structure is ready for consumption by charting libraries and
 * includes defensive defaults when optional metadata is absent.
 */
export async function getStatsTrends(init?: RequestInit): Promise<StatsTrendsResponse> {
  const apiUrl = getApiBaseUrl();
  try {
    const response = await fetchWithRetry(
      `${apiUrl}/stats/trends`,
      buildRequestInit(init)
    );
    const payload = await response.json();
    return normalizeTrends(payload);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw ApiError.fromNetworkError(
      error instanceof Error ? error : new Error(String(error))
    );
  }
}

export async function getFavoriteCollections(
  userId: string,
  init?: RequestInit
): Promise<FavoriteCollectionListResponse> {
  const apiUrl = getApiBaseUrl();
  const params = new URLSearchParams();
  params.set("user_id", userId);

  try {
    const response = await fetchWithRetry(
      `${apiUrl}/favorites/collections?${params.toString()}`,
      buildRequestInit(init)
    );
    const payload = await response.json();
    return normalizeFavoriteCollectionList(payload);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw ApiError.fromNetworkError(
      error instanceof Error ? error : new Error(String(error))
    );
  }
}

export async function getFavoriteCollectionDetail(
  collectionId: number,
  userId?: string,
  init?: RequestInit
): Promise<FavoriteCollectionDetail> {
  const apiUrl = getApiBaseUrl();
  const params = new URLSearchParams();
  if (userId && userId.trim().length > 0) {
    params.set("user_id", userId);
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";

  try {
    const response = await fetchWithRetry(
      `${apiUrl}/favorites/collections/${collectionId}${suffix}`,
      buildRequestInit(init)
    );

    if (response.status === 404) {
      throw new NotFoundError(
        "FavoriteCollection",
        `Collection ${collectionId} not found`
      );
    }

    const payload = await response.json();
    const detail = normalizeFavoriteCollectionDetail(payload);
    if (!detail) {
      throw new ApiError("Malformed favorites collection payload", {
        statusCode: 500,
        detail: "Unable to normalise favorites collection response",
      });
    }
    return detail;
  } catch (error) {
    if (error instanceof ApiError || error instanceof NotFoundError) {
      throw error;
    }
    if (error instanceof Error && error.name === "SyntaxError") {
      throw ApiError.fromParseError(error);
    }
    throw ApiError.fromNetworkError(
      error instanceof Error ? error : new Error(String(error))
    );
  }
}

export async function createFavoriteCollection(
  payload: FavoriteCollectionCreatePayload,
  init?: RequestInit
): Promise<FavoriteCollectionDetail> {
  const apiUrl = getApiBaseUrl();
  try {
    const response = await fetchWithRetry(`${apiUrl}/favorites/collections`, {
      ...buildRequestInit(init),
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    const detail = normalizeFavoriteCollectionDetail(data);
    if (!detail) {
      throw new ApiError("Malformed favorites collection payload", {
        statusCode: 500,
        detail: "Unable to normalise favorites collection response",
      });
    }
    return detail;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === "SyntaxError") {
      throw ApiError.fromParseError(error);
    }
    throw ApiError.fromNetworkError(
      error instanceof Error ? error : new Error(String(error))
    );
  }
}

export async function addFavoriteEntry(
  collectionId: number,
  payload: FavoriteEntryCreatePayload,
  userId?: string,
  init?: RequestInit
): Promise<FavoriteEntry> {
  const apiUrl = getApiBaseUrl();
  const params = new URLSearchParams();
  if (userId && userId.trim().length > 0) {
    params.set("user_id", userId);
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";

  try {
    const response = await fetchWithRetry(
      `${apiUrl}/favorites/collections/${collectionId}/entries${suffix}`,
      {
        ...buildRequestInit(init),
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(init?.headers ?? {}),
        },
        body: JSON.stringify(payload),
      }
    );
    const data = await response.json();
    const entry = normalizeFavoriteEntry(data);
    if (!entry) {
      throw new ApiError("Malformed favorites entry payload", {
        statusCode: 500,
        detail: "Unable to normalise favorites entry response",
      });
    }
    return entry;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === "SyntaxError") {
      throw ApiError.fromParseError(error);
    }
    throw ApiError.fromNetworkError(
      error instanceof Error ? error : new Error(String(error))
    );
  }
}

export async function reorderFavoriteEntries(
  collectionId: number,
  payload: FavoriteEntryReorderPayload,
  userId?: string,
  init?: RequestInit
): Promise<FavoriteCollectionDetail> {
  const apiUrl = getApiBaseUrl();
  const params = new URLSearchParams();
  if (userId && userId.trim().length > 0) {
    params.set("user_id", userId);
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";

  try {
    const response = await fetchWithRetry(
      `${apiUrl}/favorites/collections/${collectionId}/entries/reorder${suffix}`,
      {
        ...buildRequestInit(init),
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(init?.headers ?? {}),
        },
        body: JSON.stringify(payload),
      }
    );
    const data = await response.json();
    const detail = normalizeFavoriteCollectionDetail(data);
    if (!detail) {
      throw new ApiError("Malformed favorites collection payload", {
        statusCode: 500,
        detail: "Unable to normalise favorites collection response",
      });
    }
    return detail;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === "SyntaxError") {
      throw ApiError.fromParseError(error);
    }
    throw ApiError.fromNetworkError(
      error instanceof Error ? error : new Error(String(error))
    );
  }
}

export async function updateFavoriteEntry(
  collectionId: number,
  entryId: number,
  payload: FavoriteEntryUpdatePayload,
  userId?: string,
  init?: RequestInit
): Promise<FavoriteEntry> {
  const apiUrl = getApiBaseUrl();
  const params = new URLSearchParams();
  if (userId && userId.trim().length > 0) {
    params.set("user_id", userId);
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";

  try {
    const response = await fetchWithRetry(
      `${apiUrl}/favorites/collections/${collectionId}/entries/${entryId}${suffix}`,
      {
        ...buildRequestInit(init),
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(init?.headers ?? {}),
        },
        body: JSON.stringify(payload),
      }
    );
    const data = await response.json();
    const entry = normalizeFavoriteEntry(data);
    if (!entry) {
      throw new ApiError("Malformed favorites entry payload", {
        statusCode: 500,
        detail: "Unable to normalise favorites entry response",
      });
    }
    return entry;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === "SyntaxError") {
      throw ApiError.fromParseError(error);
    }
    throw ApiError.fromNetworkError(
      error instanceof Error ? error : new Error(String(error))
    );
  }
}

export async function deleteFavoriteEntry(
  collectionId: number,
  entryId: number,
  userId?: string,
  init?: RequestInit
): Promise<void> {
  const apiUrl = getApiBaseUrl();
  const params = new URLSearchParams();
  if (userId && userId.trim().length > 0) {
    params.set("user_id", userId);
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";

  try {
    await fetchWithRetry(
      `${apiUrl}/favorites/collections/${collectionId}/entries/${entryId}${suffix}`,
      {
        ...buildRequestInit(init),
        method: "DELETE",
        headers: {
          ...(init?.headers ?? {}),
        },
      }
    );
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw ApiError.fromNetworkError(
      error instanceof Error ? error : new Error(String(error))
    );
  }
}

export async function getFightGraph(
  params: FightGraphQueryParams = {},
  init?: RequestInit
): Promise<FightGraphResponse> {
  const apiUrl = getApiBaseUrl();
  const searchParams = new URLSearchParams();

  if (params.division && params.division.trim().length > 0) {
    searchParams.set("division", params.division);
  }
  if (typeof params.startYear === "number") {
    searchParams.set("start_year", String(params.startYear));
  }
  if (typeof params.endYear === "number") {
    searchParams.set("end_year", String(params.endYear));
  }
  if (typeof params.limit === "number") {
    searchParams.set("limit", String(params.limit));
  }
  if (typeof params.includeUpcoming === "boolean") {
    searchParams.set("include_upcoming", params.includeUpcoming ? "true" : "false");
  }

  const query = searchParams.toString();
  const endpoint = query.length > 0 ? `${apiUrl}/fightweb/graph?${query}` : `${apiUrl}/fightweb/graph`;

  try {
    const response = await fetchWithRetry(endpoint, buildRequestInit(init));
    const payload = await response.json();
    return normalizeFightGraphResponse(payload);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === "SyntaxError") {
      throw ApiError.fromParseError(error);
    }
    throw ApiError.fromNetworkError(
      error instanceof Error ? error : new Error(String(error))
    );
  }
}

export async function compareFighters(
  fighterIds: string[]
): Promise<FighterComparisonResponse> {
  if (fighterIds.length < 2) {
    throw new ApiError("Select at least two fighters to compare.", {
      statusCode: 400,
      detail: "Comparison requires at least two fighter IDs",
    });
  }

  const apiUrl = getApiBaseUrl();
  const params = new URLSearchParams();
  fighterIds.forEach((id) => {
    if (id) {
      params.append("fighter_ids", id);
    }
  });

  try {
    const response = await fetchWithRetry(
      `${apiUrl}/fighters/compare?${params.toString()}`,
      buildRequestInit()
    );

    const payload = await response.json();
    if (!isRecord(payload)) {
      return { fighters: [] };
    }

    const fightersSource = Array.isArray(payload.fighters) ? payload.fighters : [];
    const fighters = fightersSource
      .map((entry) => normalizeComparisonEntry(entry))
      .filter((entry): entry is FighterComparisonEntry => entry !== null);

    return { fighters };
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw ApiError.fromNetworkError(
      error instanceof Error ? error : new Error(String(error))
    );
  }
}
