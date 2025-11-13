"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  resolveDivisionGlow,
  type ColorVisionMode,
  type DivisionColorRamp,
} from "@/constants/divisionColors";
import { useColorVisionMode } from "@/hooks/useColorVisionMode";
import type { FightGraphResponse } from "@/lib/types";

import {
  colorForDivision,
  computeForceLayout,
  createDivisionColorScale,
  type LayoutEdge,
  type LayoutNode,
} from "./graph-layout";

type FightGraphCanvasProps = {
  data: FightGraphResponse | null;
  isLoading?: boolean;
  selectedNodeId?: string | null;
  onSelectNode?: (nodeId: string | null) => void;
  palette?: Map<string, DivisionColorRamp> | null;
  nodeColorMap?: Map<string, string> | null;
  isolatedDivision?: string | null;
  minFightsThreshold?: number; // Add this prop
};

type TooltipState = {
  x: number;
  y: number;
  node: RenderNode;
} | null;

interface RenderNode extends LayoutNode {
  px: number;
  py: number;
}

interface RenderEdge extends LayoutEdge {
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  sourceDivision: string | null | undefined;
  targetDivision: string | null | undefined;
}

const CANVAS_HEIGHT = 520;

export function FightGraphCanvas({
  data,
  isLoading = false,
  selectedNodeId = null,
  onSelectNode,
  palette: paletteProp = null,
  nodeColorMap = null,
  isolatedDivision = null,
  minFightsThreshold = 2, // Default: show edges with 2+ fights
}: FightGraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [size, setSize] = useState<{ width: number; height: number }>({
    width: 800,
    height: CANVAS_HEIGHT,
  });
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<TooltipState>(null);
  const [transform, setTransform] = useState<{
    scale: number;
    translateX: number;
    translateY: number;
  }>({
    scale: 1,
    translateX: 0,
    translateY: 0,
  });
  const [isPanning, setIsPanning] = useState(false);
  const colorVisionMode = useColorVisionMode();
  const panOrigin = useRef<{
    x: number;
    y: number;
    translateX: number;
    translateY: number;
    pointerId: number | null;
  }>({ x: 0, y: 0, translateX: 0, translateY: 0, pointerId: null });

  useEffect(() => {
    const element = containerRef.current;
    if (!element) {
      return;
    }
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) {
        return;
      }
      setSize({
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      });
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const layout = useMemo(() => {
    if (!data) {
      return null;
    }
    if (data.nodes.length === 0) {
      return null;
    }
    return computeForceLayout(data.nodes, data.links);
  }, [data]);

  const palette = useMemo(() => {
    if (paletteProp) {
      return paletteProp;
    }
    if (!data) {
      return new Map<string, DivisionColorRamp>();
    }
    return createDivisionColorScale(data.nodes);
  }, [data, paletteProp]);

  const focusNodeId = hoveredNodeId ?? selectedNodeId ?? null;
  const isolatedKey = useMemo(() => {
    if (!isolatedDivision) {
      return null;
    }
    const trimmed = isolatedDivision.trim();
    return trimmed.length > 0 ? trimmed : null;
  }, [isolatedDivision]);

  const renderGraph = useMemo(() => {
    if (!layout) {
      return null;
    }
    const padding = 48;
    const width = Math.max(size.width, padding * 2 + 10);
    const height = Math.max(size.height, padding * 2 + 10);
    const xRange = layout.bounds.maxX - layout.bounds.minX;
    const yRange = layout.bounds.maxY - layout.bounds.minY;
    const safeXRange = xRange === 0 ? 1 : xRange;
    const safeYRange = yRange === 0 ? 1 : yRange;

    const nodes: RenderNode[] = layout.nodes.map((node) => {
      const xRatio = (node.x - layout.bounds.minX) / safeXRange;
      const yRatio = (node.y - layout.bounds.minY) / safeYRange;
      const px = padding + xRatio * (width - padding * 2);
      const py = padding + yRatio * (height - padding * 2);
      return {
        ...node,
        px,
        py,
      };
    });

    const nodeMap = new Map<string, RenderNode>();
    for (const node of nodes) {
      nodeMap.set(node.id, node);
    }

    const edges: RenderEdge[] = layout.edges
      .filter((edge) => {
        // Always show edges connected to focused node
        if (focusNodeId && (edge.source === focusNodeId || edge.target === focusNodeId)) {
          return true;
        }
        // Filter by minimum fight threshold
        return edge.fights >= minFightsThreshold;
      })
      .map((edge) => {
        const source = nodeMap.get(edge.source);
        const target = nodeMap.get(edge.target);
        if (!source || !target) {
          return null;
        }
        return {
          ...edge,
          sourceX: source.px,
          sourceY: source.py,
          targetX: target.px,
          targetY: target.py,
          sourceDivision: source.division,
          targetDivision: target.division,
        };
      })
      .filter((edge): edge is RenderEdge => edge !== null);

    return { nodes, edges, nodeMap };
  }, [
    layout,
    size.height,
    size.width,
    focusNodeId,
    minFightsThreshold,
  ]);

  const nodeMap = useMemo(() => {
    if (!renderGraph) {
      return new Map<string, RenderNode>();
    }
    return renderGraph.nodeMap;
  }, [renderGraph]);
  const focusNeighbors = useMemo(() => {
    if (!focusNodeId || nodeMap.size === 0) {
      return new Set<string>();
    }
    const node = nodeMap.get(focusNodeId);
    if (!node) {
      return new Set<string>();
    }
    return new Set<string>([node.id, ...node.neighbors]);
  }, [focusNodeId, nodeMap]);

  useEffect(() => {
    if (!selectedNodeId) {
      setTooltip((current) =>
        current && current.node.id === selectedNodeId ? null : current,
      );
    }
  }, [selectedNodeId]);

  const handleNodePointerEnter = useCallback(
    (node: RenderNode, event: React.PointerEvent<SVGCircleElement>) => {
      setHoveredNodeId(node.id);
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) {
        setTooltip({ node, x: node.px, y: node.py });
        return;
      }
      setTooltip({
        node,
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
      });
    },
    [],
  );

  const handleNodePointerLeave = useCallback(() => {
    setHoveredNodeId(null);
    setTooltip(null);
  }, []);

  const handleNodeClick = useCallback(
    (node: RenderNode, event: React.MouseEvent<SVGCircleElement>) => {
      event.stopPropagation();
      const next = selectedNodeId === node.id ? null : node.id;
      onSelectNode?.(next);
    },
    [onSelectNode, selectedNodeId],
  );

  const handleBackgroundClick = useCallback(() => {
    onSelectNode?.(null);
  }, [onSelectNode]);

  const handleWheel = useCallback((event: React.WheelEvent<SVGSVGElement>) => {
    event.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) {
      return;
    }
    const pointerX = event.clientX - rect.left;
    const pointerY = event.clientY - rect.top;

    setTransform((prev) => {
      const zoomFactor = event.deltaY < 0 ? 1.1 : 0.9;
      const nextScale = Math.min(3.2, Math.max(0.55, prev.scale * zoomFactor));
      const scaleRatio = nextScale / prev.scale;
      const translateX = pointerX - scaleRatio * (pointerX - prev.translateX);
      const translateY = pointerY - scaleRatio * (pointerY - prev.translateY);
      return {
        scale: nextScale,
        translateX,
        translateY,
      };
    });
  }, []);

  const handlePointerDown = useCallback(
    (event: React.PointerEvent<SVGSVGElement>) => {
      const target = event.target as Element | null;
      if (target && target.closest("[data-node]")) {
        return;
      }
      setTooltip(null);
      setIsPanning(true);
      panOrigin.current = {
        x: event.clientX,
        y: event.clientY,
        translateX: transform.translateX,
        translateY: transform.translateY,
        pointerId: event.pointerId,
      };
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    [transform.translateX, transform.translateY],
  );

  const handlePointerMove = useCallback(
    (event: React.PointerEvent<SVGSVGElement>) => {
      if (!isPanning || panOrigin.current.pointerId !== event.pointerId) {
        return;
      }
      const dx = event.clientX - panOrigin.current.x;
      const dy = event.clientY - panOrigin.current.y;
      setTransform((prev) => ({
        ...prev,
        translateX: panOrigin.current.translateX + dx,
        translateY: panOrigin.current.translateY + dy,
      }));
    },
    [isPanning],
  );

  const endPan = useCallback((event: React.PointerEvent<SVGSVGElement>) => {
    if (panOrigin.current.pointerId !== event.pointerId) {
      return;
    }
    setIsPanning(false);
    panOrigin.current.pointerId = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
  }, []);

  const nodeRadius = useCallback((node: RenderNode) => {
    const fights = Math.max(1, node.total_fights ?? 1);
    const fightContribution = Math.min(5, Math.sqrt(fights) * 0.5);
    const degreeContribution = Math.min(4, Math.sqrt(node.degree + 1) * 0.6);
    return 3 + Math.max(fightContribution, degreeContribution);
  }, []);

  if (!data || !renderGraph) {
    return (
      <div
        ref={containerRef}
        className="flex h-[520px] w-full flex-col rounded-3xl border border-border/80 bg-muted/10 p-6"
      >
        <div className="flex items-center justify-between text-xs uppercase tracking-[0.3em] text-muted-foreground/90">
          <span>FightWeb Graph</span>
        </div>
        <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-muted-foreground">
          <span>
            We could not find enough data to construct the fight network.
          </span>
        </div>
      </div>
    );
  }

  const statusLabel = `${data.nodes.length} fighters • ${data.links.length} connections`;

  return (
    <div
      ref={containerRef}
      className="relative flex h-[520px] w-full flex-col overflow-hidden rounded-3xl border border-border/80 bg-card/60"
    >
      <header className="flex items-center justify-between px-6 py-4 text-xs uppercase tracking-[0.3em] text-muted-foreground/90">
        <span>FightWeb Graph</span>
        <span>{statusLabel}</span>
      </header>
      <div className="relative flex-1">
        <svg
          ref={svgRef}
          role="presentation"
          className={`h-full w-full touch-pan-y select-none ${
            isPanning ? "cursor-grabbing" : "cursor-grab"
          }`}
          onClick={handleBackgroundClick}
          onWheel={handleWheel}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={endPan}
          onPointerLeave={endPan}
        >
          <rect
            width="100%"
            height="100%"
            fill="transparent"
            pointerEvents="fill"
          />
          <g
            style={{
              transform: `translate(${transform.translateX}px, ${transform.translateY}px) scale(${transform.scale})`,
              transformOrigin: "0 0",
              transition: isPanning ? "none" : "transform 0.05s linear",
            }}
          >
            {renderGraph.edges.map((edge) => {
              const isConnected =
                focusNodeId !== null &&
                (edge.source === focusNodeId || edge.target === focusNodeId);

              const edgeTouchesIsolation =
                !isolatedKey ||
                (edge.sourceDivision?.trim() === isolatedKey ||
                  edge.targetDivision?.trim() === isolatedKey);

              // Much lower base opacity to reduce visual noise
              const baseOpacity = focusNodeId
                ? isConnected
                  ? 0.9
                  : 0.08
                : 0.2;
              const isolationOpacity = edgeTouchesIsolation ? 1 : 0.1;

              // Thinner edges for weaker connections
              const strokeWidth = focusNodeId && isConnected
                ? Math.min(6, 1.5 + Math.log(edge.fights + 1) * 1.2)
                : Math.min(2, 0.8 + Math.log(edge.fights + 1) * 0.4);
              
              // Calculate control point for curve (perpendicular midpoint)
              const dx = edge.targetX - edge.sourceX;
              const dy = edge.targetY - edge.sourceY;
              const midX = (edge.sourceX + edge.targetX) / 2;
              const midY = (edge.sourceY + edge.targetY) / 2;
              const curveOffset = 20; // Curve strength
              const controlX = midX + (-dy * curveOffset) / Math.sqrt(dx * dx + dy * dy);
              const controlY = midY + (dx * curveOffset) / Math.sqrt(dx * dx + dy * dy);
              
              const pathData = `M ${edge.sourceX} ${edge.sourceY} Q ${controlX} ${controlY} ${edge.targetX} ${edge.targetY}`;
              
              return (
                <path
                  key={`${edge.source}-${edge.target}`}
                  d={pathData}
                  fill="none"
                  stroke="hsl(var(--foreground) / 0.4)"  // Lighter color
                  strokeWidth={strokeWidth}
                  strokeOpacity={baseOpacity * isolationOpacity}
                  strokeLinecap="round"
                  pointerEvents="none"
                  style={{
                    transition: focusNodeId ? "opacity 0.2s ease, stroke-width 0.2s ease" : "none",
                  }}
                />
              );
            })}

            {renderGraph.nodes.map((node) => {
              const isFocus = focusNodeId === node.id;
              const isNeighbor =
                focusNodeId !== null &&
                focusNeighbors.has(node.id) &&
                node.id !== focusNodeId;
              const divisionKey = node.division?.trim() ?? null;
              const matchesIsolation = !isolatedKey || divisionKey === isolatedKey;
              const baseOpacity =
                focusNodeId === null
                  ? 0.95
                  : isFocus || isNeighbor
                    ? 0.95
                    : 0.2;
              const opacity = matchesIsolation ? baseOpacity : Math.min(0.12, baseOpacity);
              const strokeWidth = isFocus ? 3 : isNeighbor ? 2 : 1.2;
              const fillColor =
                nodeColorMap?.get(node.id) ??
                colorForDivision(node.division, palette, colorVisionMode);
              const glowFilter = computeNodeGlow(
                node,
                palette,
                colorVisionMode,
              );

              return (
                <g key={node.id}>
                  <circle
                    data-node="true"
                    cx={node.px}
                    cy={node.py}
                    r={nodeRadius(node)}
                    fill={fillColor}
                    stroke="var(--background)"
                    strokeWidth={strokeWidth}
                    opacity={opacity}
                    style={glowFilter ? { filter: glowFilter } : undefined}
                    onPointerEnter={(event) =>
                      handleNodePointerEnter(node, event)
                    }
                    onPointerMove={(event) =>
                      handleNodePointerEnter(node, event)
                    }
                    onPointerLeave={handleNodePointerLeave}
                    onClick={(event) => handleNodeClick(node, event)}
                  />
                  {isFocus ? (
                    <circle
                      cx={node.px}
                      cy={node.py}
                      r={nodeRadius(node) + 8}
                      fill="none"
                      stroke={fillColor}
                      strokeOpacity={0.25}
                      strokeWidth={2}
                      pointerEvents="none"
                    />
                  ) : null}
                </g>
              );
            })}
          </g>
        </svg>

        {tooltip ? (
          <div
            style={{
              left: tooltip.x + 12,
              top: tooltip.y + 12,
            }}
            className="pointer-events-none absolute z-20 max-w-xs rounded-xl border border-border/80 bg-background/95 p-3 text-xs shadow-lg"
          >
            <div className="font-semibold">{tooltip.node.name}</div>
            <div className="text-muted-foreground">
              {tooltip.node.record ?? "Record unavailable"}
            </div>
            <div className="mt-1 text-muted-foreground/80">
              {tooltip.node.division ?? "Unknown division"}
            </div>
            <div className="mt-2 flex items-center justify-between text-muted-foreground/70">
              <span>Fights</span>
              <span>{tooltip.node.total_fights}</span>
            </div>
          </div>
        ) : null}

        {isLoading ? (
          <div className="absolute inset-0 z-30 flex items-center justify-center bg-background/60 backdrop-blur-sm">
            <div className="flex items-center gap-3 rounded-full border border-border/60 bg-card px-4 py-2 text-sm text-muted-foreground">
              <span className="h-2 w-2 animate-ping rounded-full bg-foreground/80" />
              Updating graph…
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function normalizeRankValue(rank: number | null | undefined): number | null {
  if (rank === null || rank === undefined) {
    return null;
  }
  if (rank <= 0) {
    return 1;
  }
  const scaled = 1 - Math.min(1, (rank - 1) / 14);
  return Number.isFinite(scaled) ? scaled : null;
}

function computeNodeGlow(
  node: RenderNode,
  palette: Map<string, DivisionColorRamp>,
  mode: ColorVisionMode,
): string | null {
  const current = normalizeRankValue(node.current_rank);
  const peak = normalizeRankValue(node.peak_rank);
  const weight =
    current !== null
      ? current
      : peak !== null
        ? peak * 0.6
        : null;

  if (weight === null || weight <= 0) {
    return null;
  }

  const divisionKey = node.division?.trim() ?? null;
  const ramp = divisionKey ? palette.get(divisionKey) ?? null : null;
  const glowHex = ramp?.glow ?? resolveDivisionGlow(divisionKey);
  const blurRadius = 6 + weight * 10;
  const alpha = Math.min(
    1,
    (mode === "colorblind" ? 0.35 : 0.25) + weight * 0.35,
  );
  return `drop-shadow(0 0 ${blurRadius.toFixed(2)}px ${hexToRgba(glowHex, alpha)})`;
}

function hexToRgba(hex: string, alpha: number): string {
  const normalized = hex.replace("#", "");
  const r = Number.parseInt(normalized.slice(0, 2), 16);
  const g = Number.parseInt(normalized.slice(2, 4), 16);
  const b = Number.parseInt(normalized.slice(4, 6), 16);
  const clampedAlpha = Math.min(1, Math.max(0, alpha));
  return `rgba(${r}, ${g}, ${b}, ${clampedAlpha.toFixed(2)})`;
}
