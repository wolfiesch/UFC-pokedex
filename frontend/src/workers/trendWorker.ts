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
type Comparator<T> = (a: T, b: T) => number;

class Heap<T> {
  private data: T[] = [];

  constructor(private readonly compare: Comparator<T>) {}

  push(value: T): void {
    this.data.push(value);
    this.heapifyUp();
  }

  peek(): T | undefined {
    return this.data[0];
  }

  pop(): T | undefined {
    if (this.data.length === 0) {
      return undefined;
    }

    const top = this.data[0];
    const end = this.data.pop();
    if (this.data.length > 0 && end !== undefined) {
      this.data[0] = end;
      this.heapifyDown();
    }
    return top;
  }

  size(): number {
    return this.data.length;
  }

  private heapifyUp(): void {
    let index = this.data.length - 1;
    while (index > 0) {
      const parentIndex = Math.floor((index - 1) / 2);
      if (this.compare(this.data[index], this.data[parentIndex]) >= 0) {
        break;
      }
      [this.data[index], this.data[parentIndex]] = [
        this.data[parentIndex],
        this.data[index],
      ];
      index = parentIndex;
    }
  }

  private heapifyDown(): void {
    let index = 0;
    while (true) {
      const left = index * 2 + 1;
      const right = left + 1;
      let smallest = index;

      if (
        left < this.data.length &&
        this.compare(this.data[left], this.data[smallest]) < 0
      ) {
        smallest = left;
      }

      if (
        right < this.data.length &&
        this.compare(this.data[right], this.data[smallest]) < 0
      ) {
        smallest = right;
      }

      if (smallest === index) {
        break;
      }

      [this.data[index], this.data[smallest]] = [
        this.data[smallest],
        this.data[index],
      ];
      index = smallest;
    }
  }
}

class SlidingMedian {
  private readonly lower = new Heap<number>((a, b) => b - a); // Max heap
  private readonly upper = new Heap<number>((a, b) => a - b); // Min heap
  private lowerSize = 0;
  private upperSize = 0;
  private readonly pendingRemovals = new Map<number, number>();

  add(value: number): void {
    if (this.lower.size() === 0 || value <= (this.lower.peek() ?? value)) {
      this.lower.push(value);
      this.lowerSize += 1;
    } else {
      this.upper.push(value);
      this.upperSize += 1;
    }
    this.rebalance();
  }

  remove(value: number): void {
    this.pendingRemovals.set(value, (this.pendingRemovals.get(value) ?? 0) + 1);

    if (this.lower.size() > 0 && value <= (this.lower.peek() ?? value)) {
      this.lowerSize -= 1;
      if (value === this.lower.peek()) {
        this.prune(this.lower);
      }
    } else {
      this.upperSize -= 1;
      if (value === this.upper.peek()) {
        this.prune(this.upper);
      }
    }

    this.rebalance();
  }

  getMedian(windowLength: number): number {
    if (windowLength === 0) {
      return 0;
    }

    this.prune(this.lower);
    this.prune(this.upper);

    if (windowLength % 2 === 1) {
      return this.lower.peek() ?? 0;
    }

    const lowerValue = this.lower.peek() ?? 0;
    const upperValue = this.upper.peek() ?? lowerValue;
    return (lowerValue + upperValue) / 2;
  }

  private prune(heap: Heap<number>): void {
    while (heap.size() > 0) {
      const value = heap.peek();
      if (value === undefined) {
        break;
      }

      const removals = this.pendingRemovals.get(value);
      if (!removals) {
        break;
      }

      if (removals === 1) {
        this.pendingRemovals.delete(value);
      } else {
        this.pendingRemovals.set(value, removals - 1);
      }

      heap.pop();
    }
  }

  private rebalance(): void {
    this.prune(this.lower);
    this.prune(this.upper);

    if (this.lowerSize > this.upperSize + 1) {
      const value = this.lower.pop();
      if (value !== undefined) {
        this.upper.push(value);
        this.lowerSize -= 1;
        this.upperSize += 1;
      }
    } else if (this.upperSize > this.lowerSize) {
      const value = this.upper.pop();
      if (value !== undefined) {
        this.lower.push(value);
        this.upperSize -= 1;
        this.lowerSize += 1;
      }
    }
  }
}

function computeRollingMedian(
  points: TrendPoint[],
  windowSize: number = 5
): TrendPoint[] {
  if (points.length === 0) {
    return [];
  }

  if (points.length <= windowSize) {
    const sortedY = points.map((p) => p.y).sort((a, b) => a - b);
    const medianY = sortedY[Math.floor(sortedY.length / 2)];
    const medianX = points[Math.floor(points.length / 2)].x;
    return [{ x: medianX, y: medianY }];
  }

  const smoothed: TrendPoint[] = [];
  const halfWindow = Math.floor(windowSize / 2);
  const yValues = points.map((point) => point.y);
  const slidingMedian = new SlidingMedian();

  let currentStart = 0;
  let currentEnd = 0;

  for (let i = 0; i < points.length; i += 1) {
    const targetStart = Math.max(0, i - halfWindow);
    const targetEnd = Math.min(points.length, i + halfWindow + 1);

    while (currentEnd < targetEnd) {
      slidingMedian.add(yValues[currentEnd]);
      currentEnd += 1;
    }

    while (currentStart < targetStart) {
      slidingMedian.remove(yValues[currentStart]);
      currentStart += 1;
    }

    while (currentEnd > targetEnd) {
      currentEnd -= 1;
      slidingMedian.remove(yValues[currentEnd]);
    }

    const medianY = slidingMedian.getMedian(targetEnd - targetStart);
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
