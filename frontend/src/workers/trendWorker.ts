/* eslint-disable no-restricted-globals */
/**
 * Dedicated worker responsible for smoothing the finish time trajectory.
 * The worker keeps the expensive math off the main thread so that the scatter
 * plot can remain at 60 fps during interaction.
 */
declare const self: DedicatedWorkerGlobalScope;

export interface TrendWorkerComputeMessage {
  type: 'compute';
  points: { x: number; y: number }[];
  window?: number;
}

export interface TrendWorkerResultMessage {
  type: 'result';
  points: { x: number; y: number }[];
}

const median = (values: number[]): number => {
  if (values.length === 0) {
    return 0;
  }
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1] + sorted[mid]) / 2;
  }
  return sorted[mid];
};

const computeRollingMedian = (
  samples: { x: number; y: number }[],
  windowSize: number,
): { x: number; y: number }[] => {
  if (samples.length === 0) {
    return [];
  }

  const halfWindow = Math.max(1, Math.floor(windowSize / 2));
  const result: { x: number; y: number }[] = [];

  for (let index = 0; index < samples.length; index += 1) {
    const start = Math.max(0, index - halfWindow);
    const end = Math.min(samples.length - 1, index + halfWindow);
    const windowValues: number[] = [];
    for (let pointer = start; pointer <= end; pointer += 1) {
      windowValues.push(samples[pointer].y);
    }
    result.push({ x: samples[index].x, y: median(windowValues) });
  }

  return result;
};

self.onmessage = (event: MessageEvent<TrendWorkerComputeMessage>) => {
  const { data } = event;
  if (!data || data.type !== 'compute') {
    return;
  }

  const sorted = [...data.points].sort((a, b) => a.x - b.x);
  const windowSize = data.window ?? Math.max(5, Math.round(sorted.length * 0.15));
  const trend = computeRollingMedian(sorted, windowSize);
  const payload: TrendWorkerResultMessage = { type: 'result', points: trend };
  self.postMessage(payload);
};

export {}; // Ensures TypeScript treats this as a module.
