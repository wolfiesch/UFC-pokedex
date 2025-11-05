/**
 * Web Worker for computing trend lines using rolling median smoothing
 * Runs off the main thread to avoid blocking UI
 */

import type {
  TrendPoint,
  TrendWorkerRequest,
  TrendWorkerResponse,
} from "@/types/fight-scatter";

/**
 * Computes rolling median for a sorted array of points
 *
 * @param points - Sorted array of {x, y} points
 * @param windowSize - Size of rolling window (default: 5)
 * @returns Smoothed points
 */
function computeRollingMedian(
  points: TrendPoint[],
  windowSize: number = 5
): TrendPoint[] {
  if (points.length === 0) {
    return [];
  }

  if (points.length < windowSize) {
    // Not enough points for windowing, return median of all
    const sortedY = points.map((p) => p.y).sort((a, b) => a - b);
    const medianY = sortedY[Math.floor(sortedY.length / 2)];
    const medianX = points[Math.floor(points.length / 2)].x;
    return [{ x: medianX, y: medianY }];
  }

  const smoothed: TrendPoint[] = [];
  const halfWindow = Math.floor(windowSize / 2);

  for (let i = 0; i < points.length; i++) {
    // Compute window bounds
    const start = Math.max(0, i - halfWindow);
    const end = Math.min(points.length, i + halfWindow + 1);

    // Extract Y values in window
    const windowY = points.slice(start, end).map((p) => p.y);

    // Sort and find median
    windowY.sort((a, b) => a - b);
    const medianIndex = Math.floor(windowY.length / 2);
    const medianY =
      windowY.length % 2 === 0
        ? (windowY[medianIndex - 1] + windowY[medianIndex]) / 2
        : windowY[medianIndex];

    smoothed.push({
      x: points[i].x,
      y: medianY,
    });
  }

  return smoothed;
}

/**
 * Message handler for worker
 */
self.addEventListener("message", (event: MessageEvent<TrendWorkerRequest>) => {
  const { type, points, windowSize = 5 } = event.data;

  if (type !== "compute") {
    const response: TrendWorkerResponse = {
      type: "error",
      error: "Invalid message type",
    };
    self.postMessage(response);
    return;
  }

  try {
    // Ensure points are sorted by X
    const sortedPoints = [...points].sort((a, b) => a.x - b.x);

    // Compute rolling median
    const smoothedPoints = computeRollingMedian(sortedPoints, windowSize);

    const response: TrendWorkerResponse = {
      type: "result",
      points: smoothedPoints,
    };

    self.postMessage(response);
  } catch (error) {
    const response: TrendWorkerResponse = {
      type: "error",
      error: error instanceof Error ? error.message : "Unknown error",
    };
    self.postMessage(response);
  }
});

export {};
