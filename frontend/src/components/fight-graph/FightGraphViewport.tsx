"use client";

import { useRef } from "react";

import type { FightGraphResponse } from "@/types/fight-graph";

import { useThreeScene, type FightGraphViewMode } from "./hooks/useThreeScene";

export interface FightGraphViewportProps {
  /** Graph payload to be visualised within the scene. */
  graph: FightGraphResponse | null;
  /** Whether the surrounding component is fetching the dataset. */
  isLoading: boolean;
  /** Any fatal error encountered when loading the graph. */
  error: Error | null;
  /** Scene presentation mode (3D or flattened 2D). */
  mode: FightGraphViewMode;
}

/**
 * Wrapper responsible for mounting the canvas node managed by Three.js.
 * The hook performs all rendering, while this component shows inline
 * messaging regarding loading state or failures.
 */
export function FightGraphViewport({
  graph,
  isLoading,
  error,
  mode,
}: FightGraphViewportProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  useThreeScene(containerRef, graph, { mode });

  return (
    <section className="relative flex h-full min-h-[480px] flex-1 overflow-hidden rounded-3xl border border-slate-800/60 bg-slate-950/60 shadow-xl">
      <div ref={containerRef} className="relative h-full w-full" />

      {isLoading && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm">
          <div className="space-y-2 text-center text-slate-200">
            <p className="text-sm font-semibold uppercase tracking-[0.4em] text-cyan-200">
              Loading fight graph
            </p>
            <p className="text-xs text-slate-400/80">
              Fetching latest connections from the API…
            </p>
          </div>
        </div>
      )}

      {error && !isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-red-950/40 backdrop-blur-sm">
          <div className="max-w-sm space-y-3 rounded-2xl border border-red-500/40 bg-red-900/30 p-6 text-center text-red-100">
            <h3 className="text-sm font-semibold uppercase tracking-[0.4em]">
              Failed to load graph
            </h3>
            <p className="text-xs text-red-100/80">{error.message}</p>
          </div>
        </div>
      )}

      {!isLoading && !error && graph && graph.nodes.length === 0 && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-slate-950/40 backdrop-blur-sm">
          <div className="space-y-2 text-center text-slate-200">
            <p className="text-sm font-semibold uppercase tracking-[0.4em] text-cyan-200">
              No fights available
            </p>
            <p className="text-xs text-slate-400/80">
              Adjust the filters to widen the search window.
            </p>
          </div>
        </div>
      )}

      <div className="pointer-events-none absolute left-6 top-6 rounded-full border border-slate-800/60 bg-slate-950/80 px-4 py-2 text-xs font-semibold uppercase tracking-[0.4em] text-slate-300">
        {mode === "3d" ? "3D View" : "2D View"}
      </div>
    </section>
  );
}
