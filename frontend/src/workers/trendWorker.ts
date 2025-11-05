/// <reference lib="webworker" />

/**
 * Dedicated web worker tasked with smoothing fight finish durations so the main thread
 * can remain responsive while heavy numerical work executes off-thread.
 */

export interface TrendWorkerRequest {
  /** Points sorted by ascending x (milliseconds since epoch). */
  points: Array<{ x: number; y: number }>;
  /** Optional smoothing span expressed as the fraction of total points to include. */
  span?: number;
}

export interface TrendWorkerResponse {
  /** LOWESS/rolling-median smoothed polyline preserving the original x positions. */
  trend: Array<{ x: number; y: number }>;
}

const ctx: DedicatedWorkerGlobalScope = self as unknown as DedicatedWorkerGlobalScope;

/**
 * Computes a rolling-median smoothing pass over the provided points.
 * The implementation purposefully avoids allocations inside the tight loop to stay
 * performant even when hundreds of points are processed.
 */
const computeRollingMedian = (
  points: Array<{ x: number; y: number }>,
  spanFraction: number,
): Array<{ x: number; y: number }> => {
  if (points.length === 0) {
    return [];
  }

  const windowSize = Math.max(3, Math.floor(points.length * spanFraction));
  const halfWindow = Math.floor(windowSize / 2);
  const sortedPoints = [...points];
  const buffer: number[] = new Array(windowSize);

  return sortedPoints.map((point, index) => {
    const start = Math.max(0, index - halfWindow);
    const end = Math.min(points.length - 1, index + halfWindow);
    let bufferLength = 0;
    for (let i = start; i <= end; i += 1) {
      buffer[bufferLength] = points[i]!.y;
      bufferLength += 1;
    }
    const slice = buffer.slice(0, bufferLength).sort((a, b) => a - b);
    const median = slice[Math.floor(slice.length / 2)] ?? point.y;
    return { x: point.x, y: median };
  });
};

ctx.addEventListener('message', (event: MessageEvent<TrendWorkerRequest>) => {
  const { points, span = 0.25 } = event.data;
  try {
    const spanFraction = Math.min(0.5, Math.max(0.05, span));
    const trend = computeRollingMedian(points, spanFraction);
    const response: TrendWorkerResponse = { trend };
    ctx.postMessage(response);
  } catch (error) {
    // Surface errors to the main thread for observability.
    ctx.postMessage({ trend: [], error: (error as Error).message });
  }
});

export {}; // Ensure the file is treated as a module.
