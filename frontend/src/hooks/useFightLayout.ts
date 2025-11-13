"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { FightGraphResponse } from "../lib/types";
import type {
  FightLayoutLinkPosition,
  FightLayoutNodePosition,
  FightLayoutProfilingStats,
  FightLayoutWorkerOptions,
  FightLayoutWorkerRequest,
  FightLayoutWorkerResponse,
} from "../types/fight-graph";

interface FightLayoutState {
  nodes: FightLayoutNodePosition[];
  links: FightLayoutLinkPosition[];
  stats: FightLayoutProfilingStats | null;
  isRunning: boolean;
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

function createWorker(): Worker | null {
  if (typeof window === "undefined") {
    return null;
  }

  return new Worker(
    new URL("../workers/fightLayout.worker.ts", import.meta.url),
    {
      type: "module",
    },
  );
}

export function useFightLayout(
  data: FightGraphResponse | null,
  { workerOptions }: UseFightLayoutOptions = {},
): UseFightLayoutResult {
  const workerRef = useRef<Worker | null>(null);
  const [state, setState] = useState<FightLayoutState>({
    nodes: [],
    links: [],
    stats: null,
    isRunning: false,
  });

  useEffect(() => {
    workerRef.current = createWorker();
    const worker = workerRef.current;
    if (!worker) {
      return () => undefined;
    }

    const handleMessage = (event: MessageEvent<FightLayoutWorkerResponse>) => {
      setState({
        nodes: event.data.nodes,
        links: event.data.links,
        stats: event.data.stats,
        isRunning: event.data.type === "TICK" && event.data.stats.alpha > 0.01,
      });
    };

    worker.addEventListener("message", handleMessage);

    return () => {
      worker.removeEventListener("message", handleMessage);
      const termination: FightLayoutWorkerRequest = { type: "TERMINATE" };
      worker.postMessage(termination);
      worker.terminate();
      workerRef.current = null;
    };
  }, []);

  const refresh = useCallback(
    (layoutData: FightGraphResponse, overrides?: FightLayoutWorkerOptions) => {
      const worker = workerRef.current;
      if (!worker) {
        return;
      }
      const message: FightLayoutWorkerRequest = {
        type: "INIT",
        nodes: layoutData.nodes,
        links: layoutData.links,
        options: { ...workerOptions, ...(overrides ?? {}) },
      };
      worker.postMessage(message);
      setState((previous) => ({ ...previous, isRunning: true }));
    },
    [workerOptions],
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
      setState({ nodes: [], links: [], stats: null, isRunning: false });
      return;
    }
    refresh(data);
  }, [data, refresh]);

  return useMemo(
    () => ({
      nodes: state.nodes,
      links: state.links,
      stats: state.stats,
      isRunning: state.isRunning,
      refresh,
      updateWorkerOptions,
    }),
    [
      refresh,
      state.links,
      state.nodes,
      state.stats,
      state.isRunning,
      updateWorkerOptions,
    ],
  );
}
