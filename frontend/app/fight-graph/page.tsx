"use client";

import { useMemo, useState, type ReactNode } from "react";
import { Box, Scan } from "lucide-react";

import { FightGraphControls } from "@/components/fight-graph/FightGraphControls";
import { FightGraphInsights } from "@/components/fight-graph/FightGraphInsights";
import { FightGraphViewport } from "@/components/fight-graph/FightGraphViewport";
import { useFightGraph } from "@/hooks/useFightGraph";
import type { FightGraphQueryParams } from "@/types/fight-graph";
import type { FightGraphViewMode } from "@/components/fight-graph/hooks/useThreeScene";

const DEFAULT_PARAMS: FightGraphQueryParams = {
  limit: 200,
  includeUpcoming: false,
};

const VIEW_MODES: Array<{ label: string; value: FightGraphViewMode; icon: ReactNode }> = [
  {
    label: "3D",
    value: "3d",
    icon: <Box className="h-4 w-4" aria-hidden />,
  },
  {
    label: "2D",
    value: "2d",
    icon: <Scan className="h-4 w-4" aria-hidden />,
  },
];

/**
 * Route entrypoint providing an immersive fight graph experience. It wires the
 * declarative form controls to the Three.js viewport via custom hooks and keeps
 * the UI aligned with the Tailwind design language used elsewhere in the app.
 */
export default function FightGraphPage() {
  const [mode, setMode] = useState<FightGraphViewMode>("3d");
  const [params, setParams] = useState<FightGraphQueryParams>(DEFAULT_PARAMS);

  const { data, isLoading, error } = useFightGraph(params);

  const headerSubtitle = useMemo(() => {
    if (isLoading) {
      return "Fetching the latest fight rivalries…";
    }
    if (error) {
      return "Unable to load graph data from the API.";
    }
    if (data) {
      return `${data.nodes.length} fighters • ${data.links.length} connections`;
    }
    return "Load the graph to explore rivalries in 3D.";
  }, [isLoading, error, data]);

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      <header className="border-b border-slate-800/60 bg-slate-950/80 px-6 py-8 shadow-2xl">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-6">
          <div className="space-y-2">
            <h1 className="text-3xl font-black uppercase tracking-[0.4em] text-slate-100">
              Fight Graph
            </h1>
            <p className="text-sm text-slate-400">{headerSubtitle}</p>
          </div>

          <nav className="flex items-center gap-3">
            {VIEW_MODES.map((view) => {
              const isActive = mode === view.value;
              return (
                <button
                  key={view.value}
                  type="button"
                  onClick={() => setMode(view.value)}
                  className={`group flex items-center gap-2 rounded-full border px-5 py-2 text-sm font-semibold uppercase tracking-[0.3em] transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 ${
                    isActive
                      ? "border-cyan-400/60 bg-cyan-500/20 text-cyan-200"
                      : "border-slate-800 bg-slate-950/60 text-slate-300 hover:border-cyan-400/50 hover:text-cyan-200"
                  }`}
                >
                  <span className="text-slate-200">{view.icon}</span>
                  {view.label} View
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 gap-6 px-6 py-8">
        <div className="grid h-full w-full grid-cols-1 gap-6 lg:grid-cols-[360px_1fr]">
          <FightGraphControls
            params={params}
            isLoading={isLoading}
            onSubmit={(nextParams) => setParams({ ...nextParams })}
          />
          <div className="flex flex-col gap-6">
            <FightGraphViewport graph={data} isLoading={isLoading} error={error} mode={mode} />
            <FightGraphInsights metadata={data?.metadata ?? null} />
          </div>
        </div>
      </main>
    </div>
  );
}
