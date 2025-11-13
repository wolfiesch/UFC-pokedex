/**
 * Utilities for Fight Scatter Visualization
 * Handles data preprocessing, hexbin computation, and fight time calculations
 */

import type { FightHistoryEntry } from "./types";
import type {
  ScatterFight,
  FightMethod,
  FightResult,
  HexbinBucket,
} from "@/types/fight-scatter";
import { resolveImageUrl } from "./utils";

/**
 * Standard round duration in seconds (5 minutes)
 */
const ROUND_DURATION_SECONDS = 300;

/**
 * Normalizes method string to standard categories
 */
function normalizeMethod(method: string): FightMethod {
  const normalized = method.toUpperCase();

  // KO/TKO variants
  if (
    normalized.includes("KO") ||
    normalized.includes("TKO") ||
    normalized.includes("KNOCKOUT")
  ) {
    return "KO";
  }

  // Submission variants
  if (normalized.includes("SUB") || normalized.includes("SUBMISSION")) {
    return "SUB";
  }

  // Decision variants
  if (
    normalized.includes("DEC") ||
    normalized.includes("DECISION") ||
    normalized.includes("UNANIMOUS") ||
    normalized.includes("SPLIT") ||
    normalized.includes("MAJORITY")
  ) {
    return "DEC";
  }

  // Everything else (DQ, NC, etc.)
  return "OTHER";
}

/**
 * Normalizes result string to W/L/D
 */
function normalizeResult(result: string): FightResult {
  const normalized = result.toUpperCase().trim();

  if (normalized === "W" || normalized === "WIN") {
    return "W";
  }
  if (normalized === "L" || normalized === "LOSS" || normalized === "LOSE") {
    return "L";
  }
  if (normalized === "D" || normalized === "DRAW") {
    return "D";
  }

  // Default to loss for unknown results (NC, DQ, etc.)
  return "L";
}

/**
 * Parses round and time string to compute total finish seconds
 * Examples:
 *   - round=3, time="2:34" → 734 seconds (2 full rounds + 2:34)
 *   - round=1, time="4:59" → 299 seconds
 *   - round=null, time=null (decision) → Uses round limit
 *
 * @param round - Round number (1-indexed)
 * @param time - Time within round (MM:SS format)
 * @param isDecision - Whether this was a decision (no finish)
 * @param roundLimit - Maximum rounds (3 or 5)
 * @returns Total seconds elapsed
 */
export function calculateFinishSeconds(
  round: number | null | undefined,
  time: string | null | undefined,
  isDecision: boolean,
  roundLimit: number = 3,
): number {
  // For decisions, return the full fight time
  if (isDecision || !round || !time) {
    return roundLimit * ROUND_DURATION_SECONDS;
  }

  // Parse time string (format: "MM:SS" or "M:SS")
  const timeParts = time.split(":");
  if (timeParts.length !== 2) {
    // Invalid format, assume end of round
    return round * ROUND_DURATION_SECONDS;
  }

  const minutes = parseInt(timeParts[0], 10);
  const seconds = parseInt(timeParts[1], 10);

  if (isNaN(minutes) || isNaN(seconds)) {
    // Invalid time, assume end of round
    return round * ROUND_DURATION_SECONDS;
  }

  // Calculate: (completed rounds) × 300 + (minutes × 60) + seconds
  const completedRounds = round - 1;
  const timeInCurrentRound = minutes * 60 + seconds;

  return completedRounds * ROUND_DURATION_SECONDS + timeInCurrentRound;
}

/**
 * Converts a FightHistoryEntry to a ScatterFight data point
 *
 * @param fight - Raw fight history entry from API
 * @param defaultHeadshotUrl - Fallback URL if opponent has no image
 * @returns ScatterFight ready for visualization
 */
export function convertFightToScatterPoint(
  fight: FightHistoryEntry,
  defaultHeadshotUrl: string = "/img/placeholder-fighter.png",
): ScatterFight {
  const method = normalizeMethod(fight.method);
  const result = normalizeResult(fight.result);
  const isDecision = method === "DEC";

  // Determine round limit (title fights are typically 5 rounds, others are 3)
  // This is a heuristic; ideally the backend would provide this
  const roundLimit = fight.event_name?.toLowerCase().includes("title") ? 5 : 3;

  const finish_seconds = calculateFinishSeconds(
    fight.round,
    fight.time,
    isDecision,
    roundLimit,
  );

  // Construct headshot URL from opponent_id or use placeholder
  // Images are served from backend at /images/fighters/{id}.jpg
  const headshot_url = fight.opponent_id
    ? (resolveImageUrl(`/images/fighters/${fight.opponent_id}.jpg`) ??
      defaultHeadshotUrl)
    : defaultHeadshotUrl;

  return {
    id: fight.fight_id,
    date: fight.event_date || new Date().toISOString(),
    finish_seconds,
    method,
    result,
    opponent_id: fight.opponent_id || null,
    opponent_name: fight.opponent,
    headshot_url,
    event_name: fight.event_name,
    round: fight.round,
    time: fight.time,
    fight_card_url: fight.fight_card_url || null,
  };
}

/**
 * Computes hexagonal bins for density heatmap
 * Uses a simple grid-based approach (not true hexagonal bins)
 *
 * @param fights - Array of scatter fights
 * @param bucketSize - Size of grid buckets in pixels (default: 50)
 * @param xMin - Minimum X value (timestamp)
 * @param xMax - Maximum X value (timestamp)
 * @param yMin - Minimum Y value (seconds)
 * @param yMax - Maximum Y value (seconds)
 * @returns Array of hexbin buckets with counts
 */
export function computeHexbins(
  fights: ScatterFight[],
  bucketSize: number = 50,
  xMin: number,
  xMax: number,
  yMin: number,
  yMax: number,
): HexbinBucket[] {
  if (fights.length === 0) {
    return [];
  }

  // Create a map to count fights in each bucket
  const bucketMap = new Map<string, number>();

  // Compute grid dimensions
  const xRange = xMax - xMin;
  const yRange = yMax - yMin;
  const xBuckets = Math.ceil(xRange / bucketSize);
  const yBuckets = Math.ceil(yRange / bucketSize);

  // Assign each fight to a bucket
  for (const fight of fights) {
    const timestamp = new Date(fight.date).getTime();
    const x = timestamp;
    const y = fight.finish_seconds;

    // Compute bucket indices
    const i = Math.floor(((x - xMin) / xRange) * xBuckets);
    const j = Math.floor(((y - yMin) / yRange) * yBuckets);

    const key = `${i},${j}`;
    bucketMap.set(key, (bucketMap.get(key) || 0) + 1);
  }

  // Convert map to array
  const buckets: HexbinBucket[] = [];
  for (const [key, count] of bucketMap.entries()) {
    const [i, j] = key.split(",").map(Number);
    buckets.push({ i, j, count });
  }

  return buckets;
}

/**
 * Generate monthly tick marks from start year to end year
 * Used for timeline axis rendering
 *
 * @param startYear - First year to generate ticks for
 * @param endYear - Last year to generate ticks for
 * @returns Array of timestamps (milliseconds) for each month
 */
export function generateMonthlyTicks(
  startYear: number,
  endYear: number,
): number[] {
  const ticks: number[] = [];
  for (let year = startYear; year <= endYear; year++) {
    for (let month = 0; month < 12; month++) {
      ticks.push(new Date(year, month, 1).getTime());
    }
  }
  return ticks;
}

/**
 * Get the earliest fight year from fight data
 *
 * @param fights - Array of scatter fights
 * @returns Earliest year with a fight
 */
export function getFirstFightYear(fights: ScatterFight[]): number {
  const validFights = fights.filter((f) => f.date);
  if (validFights.length === 0) return new Date().getFullYear();
  const dates = validFights.map((f) => new Date(f.date).getFullYear());
  return Math.min(...dates);
}

/**
 * Computes the bounding domain for fight data
 *
 * @param fights - Array of scatter fights
 * @returns Object with xMin, xMax, yMin, yMax
 */
export function computeDomain(fights: ScatterFight[]): {
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
} {
  if (fights.length === 0) {
    const now = Date.now();
    return {
      xMin: now - 365 * 24 * 60 * 60 * 1000, // 1 year ago
      xMax: now,
      yMin: 0,
      yMax: 1500, // 5 rounds max
    };
  }

  let xMin = Infinity;
  let xMax = -Infinity;
  let yMin = Infinity;
  let yMax = -Infinity;

  for (const fight of fights) {
    const timestamp = new Date(fight.date).getTime();
    xMin = Math.min(xMin, timestamp);
    xMax = Math.max(xMax, timestamp);
    yMin = Math.min(yMin, fight.finish_seconds);
    yMax = Math.max(yMax, fight.finish_seconds);
  }

  // Add 10% padding
  const xPadding = (xMax - xMin) * 0.1;
  const yPadding = (yMax - yMin) * 0.1;

  return {
    xMin: xMin - xPadding,
    xMax: xMax + xPadding,
    yMin: Math.max(0, yMin - yPadding),
    yMax: yMax + yPadding,
  };
}

/**
 * Filters fights based on result and method criteria
 *
 * @param fights - Array of scatter fights
 * @param filterResults - Results to include (empty = all)
 * @param filterMethods - Methods to include (empty = all)
 * @returns Filtered array and indices of matches
 */
export function filterFights(
  fights: ScatterFight[],
  filterResults: FightResult[] = [],
  filterMethods: FightMethod[] = [],
): { filtered: ScatterFight[]; matchIndices: Set<number> } {
  const matchIndices = new Set<number>();

  const filtered = fights.filter((fight, index) => {
    const resultMatch =
      filterResults.length === 0 || filterResults.includes(fight.result);
    const methodMatch =
      filterMethods.length === 0 || filterMethods.includes(fight.method);

    const matches = resultMatch && methodMatch;
    if (matches) {
      matchIndices.add(index);
    }

    return matches;
  });

  return { filtered, matchIndices };
}
