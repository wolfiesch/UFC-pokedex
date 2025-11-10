import { useEffect, useRef, useState } from "react";

import type { TrendPoint, TrendWorkerRequest, TrendWorkerResponse } from "@/types/fight-scatter";

interface UseTrendWorkerOptions {
  enabled: boolean;
  points: TrendPoint[];
  windowSize: number;
}

interface TrendWorkerState {
  trendPoints: TrendPoint[];
  isWorkerAvailable: boolean;
}

/**
 * Spins up the Web Worker that smooths fight duration trends. The hook exposes
 * the resulting points and gracefully degrades when Workers are unavailable
 * (SSR or legacy browsers).
 */
export function useTrendWorker({
  enabled,
  points,
  windowSize,
}: UseTrendWorkerOptions): TrendWorkerState {
  const workerRef = useRef<Worker | null>(null);
  const [trendPoints, setTrendPoints] = useState<TrendPoint[]>([]);
  const [isWorkerAvailable, setWorkerAvailable] = useState<boolean>(true);

  useEffect(() => {
    if (!enabled) {
      setTrendPoints([]);
      return;
    }

    if (typeof Worker === "undefined") {
      setWorkerAvailable(false);
      setTrendPoints([]);
      return;
    }

    const worker = new Worker(new URL("../../../workers/trendWorker.ts", import.meta.url));
    workerRef.current = worker;

    const handleMessage = (event: MessageEvent<TrendWorkerResponse>) => {
      if (event.data.type === "result" && event.data.points) {
        setTrendPoints(event.data.points);
      } else if (event.data.type === "error") {
        console.error("Trend worker error", event.data.error);
      }
    };

    worker.addEventListener("message", handleMessage);
    setWorkerAvailable(true);

    return () => {
      worker.removeEventListener("message", handleMessage);
      worker.terminate();
      workerRef.current = null;
    };
  }, [enabled]);

  useEffect(() => {
    if (!enabled || !workerRef.current || points.length === 0) {
      if (!enabled || points.length === 0) {
        setTrendPoints([]);
      }
      return;
    }

    const request: TrendWorkerRequest = {
      type: "compute",
      points,
      windowSize,
    };

    workerRef.current.postMessage(request);
  }, [enabled, points, windowSize]);

  return { trendPoints, isWorkerAvailable };
}
