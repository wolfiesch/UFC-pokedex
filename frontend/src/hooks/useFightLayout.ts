"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { buildSynchronousFightLayout } from "@/components/FightWeb/graph-layout";

import type { FightGraphResponse } from "@/lib/types";
import type {
  FightLayoutLinkPosition,
  FightLayoutNodePosition,
  FightLayoutProfilingStats,
  FightLayoutWorkerOptions,
  FightLayoutWorkerRequest,
  FightLayoutWorkerResponse,
} from "@/types/fight-graph";

type LayoutMode = "worker" | "fallback" | "error";

interface LayoutStatus {
  mode: LayoutMode;
  reason: string | null;
  error: Error | null;
}

interface FightLayoutState {
  nodes: FightLayoutNodePosition[];
  links: FightLayoutLinkPosition[];
  stats: FightLayoutProfilingStats | null;
  isRunning: boolean;
  layoutState: LayoutStatus;
}

interface UseFightLayoutOptions {
  workerOptions?: FightLayoutWorkerOptions;
}

export interface UseFightLayoutResult extends FightLayoutState {
  refresh: (
    data: FightGraphResponse,
    overrides?: FightLayoutWorkerOptions,
  ) => void;
  updateWorkerOptions: (options: FightLayoutWorkerOptions) => void;
}

const FALLBACK_TIMEOUT_MS = 2000;

function createWorker(): Worker | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    return new Worker(
      new URL("../workers/fightLayout.worker.ts", import.meta.url),
      {
        type: "module",
      },
    );
  } catch (error) {
    console.warn("Failed to create fight layout worker", error);
    return null;
  }
}

const idleWindow = (): (Window & {
  requestIdleCallback?: (
    callback: IdleRequestCallback,
    options?: IdleRequestOptions,
  ) => number;
  cancelIdleCallback?: (handle: number) => void;
}) | null => {
  if (typeof window === "undefined") {
    return null;
  }
  return window;
};

const createInitialState = (): FightLayoutState => ({
  nodes: [],
  links: [],
  stats: null,
  isRunning: false,
  layoutState: { mode: "worker", reason: null, error: null },
});

export function useFightLayout(
  data: FightGraphResponse | null,
  { workerOptions }: UseFightLayoutOptions = {},
): UseFightLayoutResult {
  const workerRef = useRef<Worker | null>(null);
  const latestDataRef = useRef<FightGraphResponse | null>(data);
  const fallbackTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fallbackJobRef = useRef<number | null>(null);

  const [state, setState] = useState<FightLayoutState>(() =>
    createInitialState(),
  );

  const clearFallbackTimer = useCallback(() => {
    if (fallbackTimeoutRef.current === null) {
      return;
    }
    if (typeof window !== "undefined") {
      window.clearTimeout(fallbackTimeoutRef.current);
    }
    fallbackTimeoutRef.current = null;
  }, []);

  const cancelScheduledFallback = useCallback(() => {
    if (fallbackJobRef.current === null) {
      return;
    }
    const idle = idleWindow();
    if (idle?.cancelIdleCallback) {
      idle.cancelIdleCallback(fallbackJobRef.current);
    } else if (typeof window !== "undefined") {
      window.clearTimeout(fallbackJobRef.current);
    }
    fallbackJobRef.current = null;
  }, []);

  const runSynchronousFallback = useCallback(
    (
      payload?: FightGraphResponse | null,
      reason?: string,
      error?: Error | null,
    ) => {
      const graph = payload ?? latestDataRef.current;
      clearFallbackTimer();
      cancelScheduledFallback();

      if (!graph) {
        setState((previous) => ({
          ...previous,
          nodes: [],
          links: [],
          stats: null,
          isRunning: false,
          layoutState: {
            mode: error ? "error" : "fallback",
            reason: reason ?? "No fight data is available yet.",
            error: error ?? null,
          },
        }));
        return;
      }

      const execute = () => {
        try {
          const fallbackResult = buildSynchronousFightLayout(graph);
          setState({
            nodes: fallbackResult.nodes,
            links: fallbackResult.links,
            stats: fallbackResult.stats,
            isRunning: false,
            layoutState: {
              mode: "fallback",
              reason:
                reason ??
                "Fight graph worker is unavailable. Showing a simplified layout.",
              error: error ?? null,
            },
          });
        } catch (fallbackError) {
          setState({
            nodes: [],
            links: [],
            stats: null,
            isRunning: false,
            layoutState: {
              mode: "error",
              reason:
                reason ??
                "Fight graph worker and fallback layout both failed to initialize.",
              error:
                fallbackError instanceof Error
                  ? fallbackError
                  : new Error("Failed to compute fallback fight layout"),
            },
          });
        }
      };

      const idle = idleWindow();
      if (idle?.requestIdleCallback) {
        fallbackJobRef.current = idle.requestIdleCallback(
          () => {
            fallbackJobRef.current = null;
            execute();
          },
          { timeout: 300 },
        );
        return;
      }

      if (typeof window !== "undefined") {
        const timeoutId = window.setTimeout(() => {
          fallbackJobRef.current = null;
          execute();
        }, 0);
        fallbackJobRef.current = timeoutId as unknown as number;
        return;
      }

      execute();
    },
    [cancelScheduledFallback, clearFallbackTimer],
  );

  const scheduleFallbackTimer = useCallback(
    (payload: FightGraphResponse) => {
      if (typeof window === "undefined") {
        return;
      }
      clearFallbackTimer();
      fallbackTimeoutRef.current = window.setTimeout(() => {
        fallbackTimeoutRef.current = null;
        runSynchronousFallback(
          payload,
          "Timed out waiting for the fight graph worker. Falling back to a simplified layout.",
        );
      }, FALLBACK_TIMEOUT_MS);
    },
    [clearFallbackTimer, runSynchronousFallback],
  );

  useEffect(() => {
    return () => {
      clearFallbackTimer();
      cancelScheduledFallback();
    };
  }, [cancelScheduledFallback, clearFallbackTimer]);

  useEffect(() => {
    latestDataRef.current = data;
  }, [data]);

  useEffect(() => {
    workerRef.current = createWorker();
    const worker = workerRef.current;

    if (!worker) {
      if (latestDataRef.current) {
        runSynchronousFallback(
          latestDataRef.current,
          "Fight graph worker is unavailable in this environment.",
        );
      }
      return () => undefined;
    }

    const handleMessage = (event: MessageEvent<FightLayoutWorkerResponse>) => {
      clearFallbackTimer();
      setState({
        nodes: event.data.nodes,
        links: event.data.links,
        stats: event.data.stats,
        isRunning: event.data.type === "TICK" && event.data.stats.alpha > 0.01,
        layoutState: { mode: "worker", reason: null, error: null },
      });
    };

    const handleError = (event: ErrorEvent) => {
      runSynchronousFallback(
        latestDataRef.current,
        "Fight graph worker crashed. Rendering a simplified layout instead.",
        event.error instanceof Error
          ? event.error
          : new Error(event.message ?? "Worker error"),
      );
    };

    worker.addEventListener("message", handleMessage);
    worker.addEventListener("error", handleError);

    return () => {
      worker.removeEventListener("message", handleMessage);
      worker.removeEventListener("error", handleError);
      try {
        const termination: FightLayoutWorkerRequest = { type: "TERMINATE" };
        worker.postMessage(termination);
      } catch {
        // Ignore termination failures
      }
      worker.terminate();
      workerRef.current = null;
    };
  }, [clearFallbackTimer, runSynchronousFallback]);

  const refresh = useCallback(
    (layoutData: FightGraphResponse, overrides?: FightLayoutWorkerOptions) => {
      latestDataRef.current = layoutData;

      if (!layoutData) {
        setState(createInitialState());
        return;
      }

      const worker = workerRef.current;
      if (!worker) {
        runSynchronousFallback(
          layoutData,
          "Fight graph worker could not be initialized. Showing a simplified layout.",
        );
        return;
      }

      const message: FightLayoutWorkerRequest = {
        type: "INIT",
        nodes: layoutData.nodes,
        links: layoutData.links,
        options: { ...workerOptions, ...(overrides ?? {}) },
      };

      try {
        worker.postMessage(message);
        setState((previous) => ({
          ...previous,
          isRunning: true,
          layoutState: { mode: "worker", reason: null, error: null },
        }));
        scheduleFallbackTimer(layoutData);
      } catch (error) {
        runSynchronousFallback(
          layoutData,
          "Failed to communicate with the fight graph worker.",
          error instanceof Error
            ? error
            : new Error("Failed to post message to worker"),
        );
      }
    },
    [runSynchronousFallback, scheduleFallbackTimer, workerOptions],
  );

  const updateWorkerOptions = useCallback(
    (options: FightLayoutWorkerOptions) => {
      const worker = workerRef.current;
      if (!worker) {
        return;
      }
      worker.postMessage({ type: "UPDATE_OPTIONS", options });
    },
    [],
  );

  useEffect(() => {
    if (!data) {
      cancelScheduledFallback();
      clearFallbackTimer();
      setState(createInitialState());
      return;
    }
    refresh(data);
  }, [cancelScheduledFallback, clearFallbackTimer, data, refresh]);

  return useMemo(
    () => ({
      nodes: state.nodes,
      links: state.links,
      stats: state.stats,
      isRunning: state.isRunning,
      layoutState: state.layoutState,
      refresh,
      updateWorkerOptions,
    }),
    [
      refresh,
      state.links,
      state.nodes,
      state.stats,
      state.isRunning,
      state.layoutState,
      updateWorkerOptions,
    ],
  );
}
