"use client";

import { useCallback, useMemo, useRef, useState } from "react";

import { useFightLayout } from "@/hooks/useFightLayout";
import type { FightGraphResponse } from "@/lib/types";
import { DEFAULT_NODE_COLOR, createDivisionColorScale } from "./graph-layout";
import { FightGraphScene } from "../fight-graph/Scene";
import {
  FightGraphViewProvider,
  useFightGraphView,
} from "../fight-graph/ViewContext";
import type { FightLayoutLinkPosition } from "@/types/fight-graph";
import { Button } from "../ui/button";
import type { ThreeEvent } from "@react-three/fiber";

interface FightGraphCanvasProps {
  data: FightGraphResponse | null;
  isLoading?: boolean;
  selectedNodeId?: string | null;
  onSelectNode?: (nodeId: string | null) => void;
  palette?: Map<string, string> | null;
  nodeColorMap?: Map<string, string> | null;
  minFightsThreshold?: number;
}

/**
 * Lightweight hover metadata captured from the Three.js pointer event so the
 * React overlay can position contextual tooltips using DOM coordinates.
 */
interface HoverState {
  nodeId: string;
  clientX: number;
  clientY: number;
}

/**
 * Filters edges to reduce clutter while still highlighting any relationships
 * touching the focused node. The logic mirrors the behaviour of the previous
 * 2D renderer so downstream interactions remain familiar.
 */
function useFilteredLinks(
  links: FightLayoutLinkPosition[],
  focusNodeId: string | null,
  minFightsThreshold: number,
): FightLayoutLinkPosition[] {
  return useMemo(() => {
    return links.filter((link) => {
      if (
        focusNodeId &&
        (link.source === focusNodeId || link.target === focusNodeId)
      ) {
        return true;
      }
      return link.fights >= minFightsThreshold;
    });
  }, [focusNodeId, links, minFightsThreshold]);
}

/**
 * Internal implementation for the graph viewport. The surrounding
 * {@link FightGraphViewProvider} supplies the shared 2D/3D projection state so
 * the UI only concerns itself with worker plumbing and UI chrome.
 */
function FightGraphCanvasInner({
  data,
  isLoading = false,
  selectedNodeId = null,
  onSelectNode,
  palette: paletteProp = null,
  nodeColorMap = null,
  minFightsThreshold = 2,
}: FightGraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [hoverState, setHoverState] = useState<HoverState | null>(null);
  const { mode, toggleMode } = useFightGraphView();

  const palette = useMemo(() => {
    if (paletteProp) {
      return paletteProp;
    }
    if (!data) {
      return new Map<string, string>();
    }
    return createDivisionColorScale(data.nodes);
  }, [data, paletteProp]);

  const workerOptions = useMemo(
    () => ({
      linkDistance: 200,
      chargeStrength: -45,
      updateIntervalMs: 26,
      zScale: 0.85,
    }),
    [],
  );

  const { nodes, links, stats, updateWorkerOptions } = useFightLayout(data, {
    workerOptions,
  });

  const focusNodeId = hoverState?.nodeId ?? selectedNodeId ?? null;
  const filteredLinks = useFilteredLinks(
    links,
    focusNodeId,
    minFightsThreshold,
  );

  const hoveredNode = useMemo(() => {
    if (!hoverState) {
      return null;
    }
    return nodes.find((node) => node.id === hoverState.nodeId) ?? null;
  }, [hoverState, nodes]);

  const handleHover = useCallback(
    (nodeId: string | null, event?: ThreeEvent<PointerEvent>) => {
      if (!nodeId || !event) {
        setHoverState(null);
        return;
      }
      const nextNode = nodes.find((node) => node.id === nodeId);
      if (!nextNode) {
        setHoverState(null);
        return;
      }
      setHoverState({
        nodeId: nextNode.id,
        clientX: event.clientX,
        clientY: event.clientY,
      });
    },
    [nodes],
  );

  const handleSelect = useCallback(
    (nodeId: string | null) => {
      onSelectNode?.(nodeId);
    },
    [onSelectNode],
  );

  const handlePerformanceDrop = useCallback(() => {
    updateWorkerOptions({ updateIntervalMs: 42, chargeStrength: -32 });
  }, [updateWorkerOptions]);

  const handlePerformanceRecover = useCallback(() => {
    updateWorkerOptions({ updateIntervalMs: 26, chargeStrength: -45 });
  }, [updateWorkerOptions]);

  const tooltipPosition = useMemo(() => {
    if (!hoverState || !containerRef.current) {
      return null;
    }
    const rect = containerRef.current.getBoundingClientRect();
    return {
      left: hoverState.clientX - rect.left + 12,
      top: hoverState.clientY - rect.top + 12,
    };
  }, [hoverState]);

  return (
    <div className="relative flex h-[520px] w-full flex-col gap-3">
      <div className="flex items-center justify-between px-4 pt-2">
        <Button variant="secondary" size="sm" onClick={toggleMode}>
          {mode === "3d" ? "Switch to 2D" : "Switch to 3D"}
        </Button>
        {stats ? (
          <div className="text-xs text-slate-400">
            tick {stats.tickCount.toFixed(0)} · avg{" "}
            {stats.meanTickMs.toFixed(2)} ms
          </div>
        ) : null}
      </div>
      <div
        ref={containerRef}
        className="relative h-full w-full overflow-hidden rounded-lg border border-slate-800 bg-slate-950/70"
      >
        {!isLoading && nodes.length === 0 ? (
          <div className="flex h-full w-full items-center justify-center text-sm text-slate-400">
            We could not find enough data to construct the fight network.
          </div>
        ) : (
          <>
            {isLoading ? (
              <div className="absolute inset-0 z-20 flex items-center justify-center bg-slate-950/80 text-sm text-slate-300">
                Computing layout…
              </div>
            ) : null}
            <FightGraphScene
          nodes={nodes}
          links={filteredLinks}
          nodeColorMap={nodeColorMap ?? null}
          palette={palette}
          selectedNodeId={selectedNodeId ?? null}
          hoveredNodeId={hoverState?.nodeId ?? null}
          defaultColor={DEFAULT_NODE_COLOR}
          onNodeHover={handleHover}
          onNodeSelect={handleSelect}
          onPerformanceDrop={handlePerformanceDrop}
          onPerformanceRecover={handlePerformanceRecover}
        />
            {hoveredNode && tooltipPosition ? (
              <div
                className="pointer-events-none absolute z-30 rounded-lg border border-slate-800 bg-slate-900/90 px-3 py-2 text-xs text-slate-100 shadow-lg"
                style={{ left: tooltipPosition.left, top: tooltipPosition.top }}
              >
                <div className="font-semibold">{hoveredNode.name}</div>
                {hoveredNode.record ? (
                  <div className="text-slate-300">{hoveredNode.record}</div>
                ) : null}
                <div className="text-slate-400">
                  Total fights: {hoveredNode.total_fights}
                </div>
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}

/**
 * Public wrapper that attaches the projection context before rendering the
 * interactive fight graph viewport.
 */
export function FightGraphCanvas(props: FightGraphCanvasProps) {
  return (
    <FightGraphViewProvider>
      <FightGraphCanvasInner {...props} />
    </FightGraphViewProvider>
  );
}
