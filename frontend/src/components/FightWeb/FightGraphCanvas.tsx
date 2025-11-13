"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { KeyboardEvent } from "react";
import { useRouter } from "next/navigation";

import { useFighterDetails } from "@/hooks/useFighterDetails";
import type { FightGraphResponse } from "@/lib/types";

import {
  FighterInsightCard,
  type FighterInsightMetadata,
  type UpcomingBoutSummary,
} from "../fight-graph/FighterInsightCard";

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
  onFilterDivisionRequest?: (division: string) => void;
  palette?: Map<string, string> | null;
  nodeColorMap?: Map<string, string> | null;
  minFightsThreshold?: number; // Add this prop
};

interface RenderNode extends LayoutNode {
  px: number;
  py: number;
}

interface RenderEdge extends LayoutEdge {
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
}

const CANVAS_HEIGHT = 520;

export function FightGraphCanvas({
  data,
  isLoading = false,
  selectedNodeId = null,
  onSelectNode,
  onFilterDivisionRequest,
  palette: paletteProp = null,
  nodeColorMap = null,
  minFightsThreshold = 2, // Default: show edges with 2+ fights
}: FightGraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [size, setSize] = useState<{ width: number; height: number }>({
    width: 800,
    height: CANVAS_HEIGHT,
  });
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [cardNodeId, setCardNodeId] = useState<string | null>(null);
  const [cardInteractionMode, setCardInteractionMode] = useState<
    "pointer" | "keyboard" | "selection" | null
  >(null);
  const [cardSize, setCardSize] = useState<{ width: number; height: number }>(
    { width: 0, height: 0 },
  );
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
  const cardRef = useRef<HTMLDivElement | null>(null);
  const cardInteractionRef = useRef(false);
  const hideTimerRef = useRef<number | null>(null);
  const hoveredNodeRef = useRef<string | null>(null);
  const selectedNodeRef = useRef<string | null>(null);

  const clearHideTimer = useCallback(() => {
    if (hideTimerRef.current !== null) {
      window.clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
  }, []);

  const scheduleCardClose = useCallback(() => {
    clearHideTimer();
    hideTimerRef.current = window.setTimeout(() => {
      if (cardInteractionRef.current) {
        return;
      }
      const selected = selectedNodeRef.current;
      if (selected) {
        setCardNodeId(selected);
        setCardInteractionMode((mode) => mode ?? "selection");
        return;
      }
      if (!hoveredNodeRef.current) {
        setCardNodeId(null);
        setCardInteractionMode(null);
      }
    }, 160);
  }, [clearHideTimer]);

  useEffect(() => {
    hoveredNodeRef.current = hoveredNodeId;
  }, [hoveredNodeId]);

  useEffect(() => {
    selectedNodeRef.current = selectedNodeId;
  }, [selectedNodeId]);

  useEffect(() => {
    return () => {
      clearHideTimer();
    };
  }, [clearHideTimer]);
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
      return new Map<string, string>();
    }
    return createDivisionColorScale(data.nodes);
  }, [data, paletteProp]);

  const focusNodeId = hoveredNodeId ?? selectedNodeId ?? null;

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
        };
      })
      .filter((edge): edge is RenderEdge => edge !== null);

    return { nodes, edges, nodeMap };
  }, [layout, size.height, size.width, focusNodeId, minFightsThreshold]); // Add minFightsThreshold

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
    if (selectedNodeId) {
      setCardNodeId(selectedNodeId);
      setCardInteractionMode((mode) => mode ?? "selection");
      return;
    }
    if (!hoveredNodeId && !cardInteractionRef.current) {
      setCardNodeId(null);
      setCardInteractionMode(null);
    }
  }, [hoveredNodeId, selectedNodeId]);

  const handleNodePointerEnter = useCallback(
    (node: RenderNode) => {
      clearHideTimer();
      cardInteractionRef.current = false;
      setHoveredNodeId(node.id);
      setCardNodeId(node.id);
      setCardInteractionMode("pointer");
    },
    [clearHideTimer],
  );

  const handleNodePointerLeave = useCallback(() => {
    setHoveredNodeId(null);
    scheduleCardClose();
  }, [scheduleCardClose]);

  const handleNodeClick = useCallback(
    (node: RenderNode, event: React.MouseEvent<SVGCircleElement>) => {
      event.stopPropagation();
      const next = selectedNodeId === node.id ? null : node.id;
      onSelectNode?.(next);
      if (next) {
        setCardNodeId(next);
        setCardInteractionMode("selection");
      } else if (!hoveredNodeRef.current) {
        setCardNodeId(null);
        setCardInteractionMode(null);
      }
    },
    [onSelectNode, selectedNodeId],
  );

  const handleBackgroundClick = useCallback(() => {
    onSelectNode?.(null);
    if (!hoveredNodeRef.current) {
      setCardNodeId(null);
      setCardInteractionMode(null);
    }
  }, [onSelectNode]);

  const handleNodeFocus = useCallback(
    (node: RenderNode) => {
      clearHideTimer();
      cardInteractionRef.current = false;
      setHoveredNodeId(node.id);
      setCardNodeId(node.id);
      setCardInteractionMode("keyboard");
    },
    [clearHideTimer],
  );

  const handleNodeBlur = useCallback(() => {
    scheduleCardClose();
  }, [scheduleCardClose]);

  const handleNodeKeyDown = useCallback(
    (node: RenderNode, event: KeyboardEvent<SVGCircleElement>) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        onSelectNode?.(node.id);
        setCardNodeId(node.id);
        setCardInteractionMode("keyboard");
      } else if (event.key === "Escape") {
        event.preventDefault();
        onSelectNode?.(null);
        if (!hoveredNodeRef.current) {
          setCardNodeId(null);
          setCardInteractionMode(null);
        }
      }
    },
    [onSelectNode],
  );

  // Determine the node powering the floating insight card. When the lookup fails the
  // card is hidden to avoid rendering stale metadata for nodes no longer in view.
  const cardNode = cardNodeId ? nodeMap.get(cardNodeId) ?? null : null;

  useEffect(() => {
    if (cardNodeId && !cardNode) {
      setCardNodeId(null);
    }
  }, [cardNode, cardNodeId]);

  const {
    details,
    isLoading: detailsLoading,
    error: detailsError,
  } = useFighterDetails(cardNodeId ?? "", Boolean(cardNodeId));

  // Upcoming fights are derived from the fighter details payload which reuses the fight
  // history data structure.  We surface only entries marked as "next"/"upcoming" to keep
  // the card focused on future bookings.
  const upcomingBouts = useMemo<UpcomingBoutSummary[] | null>(() => {
    if (!details || !details.fight_history) {
      return null;
    }
    return details.fight_history
      .filter((fight) => {
        const normalized = fight.result?.toLowerCase() ?? "";
        return (
          normalized === "next" ||
          normalized === "upcoming" ||
          normalized === "scheduled"
        );
      })
      .map((fight) => ({
        opponent: fight.opponent ?? null,
        event: fight.event_name ?? null,
        date:
          typeof fight.event_date === "string"
            ? fight.event_date
            : fight.event_date ?? null,
      }));
  }, [details]);

  const streakSummary = useMemo(() => {
    const type = details?.current_streak_type ?? "none";
    const count = details?.current_streak_count ?? 0;
    if (type === "none" || count <= 0) {
      return { type: "none" as const, label: null };
    }
    const descriptor =
      type === "win"
        ? "Win streak"
        : type === "loss"
          ? "Loss streak"
          : "Draw streak";
    return { type, label: `${descriptor} · ${count}` };
  }, [details?.current_streak_count, details?.current_streak_type]);

  // Compose the metadata bundle expected by the card.  We merge live detail data with the
  // lightweight graph node so the card still renders meaningful information during loading.
  const fighterMetadata = useMemo<FighterInsightMetadata | null>(() => {
    if (!cardNode) {
      return null;
    }
    return {
      id: cardNode.id,
      name: cardNode.name,
      imageUrl: cardNode.image_url ?? null,
      record: details?.record ?? cardNode.record ?? null,
      division: details?.division ?? cardNode.division ?? null,
      streakLabel: streakSummary.label,
      streakType: streakSummary.type,
      upcomingBouts,
    };
  }, [cardNode, details?.division, details?.record, upcomingBouts, streakSummary.label, streakSummary.type]);

  // Translate force-layout coordinates into container-relative pixel positions.  This keeps the
  // overlay aligned with the node even as the user pans or zooms the canvas.
  const projectNodeToScreen = useCallback(
    (node: RenderNode) => {
      const containerRect = containerRef.current?.getBoundingClientRect();
      const svgRect = svgRef.current?.getBoundingClientRect();
      const offsetX =
        svgRect && containerRect ? svgRect.left - containerRect.left : 0;
      const offsetY =
        svgRect && containerRect ? svgRect.top - containerRect.top : 0;
      return {
        x: node.px * transform.scale + transform.translateX + offsetX,
        y: node.py * transform.scale + transform.translateY + offsetY,
      };
    },
    [transform.scale, transform.translateX, transform.translateY],
  );

  const cardAnchor = useMemo(() => {
    if (!cardNode) {
      return null;
    }
    return projectNodeToScreen(cardNode);
  }, [cardNode, projectNodeToScreen]);

  useLayoutEffect(() => {
    if (!cardRef.current) {
      return;
    }
    const rect = cardRef.current.getBoundingClientRect();
    const nextSize = { width: rect.width, height: rect.height };
    setCardSize((prev) =>
      prev.width === nextSize.width && prev.height === nextSize.height
        ? prev
        : nextSize,
    );
  }, [cardNodeId, cardAnchor, details, detailsLoading, upcomingBouts]);

  // Calculate the final card position with a small offset and clamp the result so the overlay
  // never renders outside the viewport bounds.
  const cardPosition = useMemo(() => {
    if (!cardAnchor) {
      return null;
    }
    const offset = 16;
    const containerWidth = size.width;
    const containerHeight = size.height;
    let left = cardAnchor.x + offset;
    let top = cardAnchor.y + offset;

    if (left + cardSize.width > containerWidth - offset) {
      left = Math.max(offset, cardAnchor.x - cardSize.width - offset);
    }
    left = Math.max(offset, Math.min(left, containerWidth - offset));

    if (top + cardSize.height > containerHeight - offset) {
      top = Math.max(offset, cardAnchor.y - cardSize.height - offset);
    }
    top = Math.max(offset, Math.min(top, containerHeight - offset));

    return { left, top };
  }, [cardAnchor, cardSize.height, cardSize.width, size.height, size.width]);

  const statusMessage = useMemo(() => {
    if (detailsError) {
      return "Failed to load details";
    }
    if (detailsLoading) {
      return "Loading details…";
    }
    return null;
  }, [detailsError, detailsLoading]);

  const router = useRouter();

  const handleOpenProfile = useCallback(() => {
    if (!cardNodeId) {
      return;
    }
    router.push(`/fighters/${cardNodeId}`);
  }, [cardNodeId, router]);

  const handleFilterDivision = useCallback(() => {
    if (!onFilterDivisionRequest) {
      return;
    }
    const division = (details?.division ?? cardNode?.division ?? "").trim();
    if (!division) {
      return;
    }
    onFilterDivisionRequest(division);
  }, [cardNode?.division, details?.division, onFilterDivisionRequest]);

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
      cardInteractionRef.current = false;
      if (!selectedNodeRef.current) {
        setCardNodeId(null);
        setCardInteractionMode(null);
      }
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
              
              // Much lower base opacity to reduce visual noise
              const baseOpacity = focusNodeId
                ? isConnected ? 0.9 : 0.08  // Very dim when not connected
                : 0.2;  // Lower default opacity (was 0.45)
              
              // Thinner edges for weaker connections
              const strokeWidth = focusNodeId && isConnected
                ? Math.min(6, 1.5 + Math.log(edge.fights + 1) * 1.2)  // Thicker when focused
                : Math.min(2, 0.8 + Math.log(edge.fights + 1) * 0.4);  // Thinner by default
              
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
                  strokeOpacity={baseOpacity}
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
              const opacity =
                focusNodeId === null
                  ? 0.95
                  : isFocus || isNeighbor
                    ? 0.95
                    : 0.2;
              const strokeWidth = isFocus ? 3 : isNeighbor ? 2 : 1.2;
              // Use nodeColorMap if available (for recency-based coloring in single division),
              // otherwise fall back to division-based coloring
              const fillColor =
                nodeColorMap?.get(node.id) ??
                colorForDivision(node.division, palette);

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
                    onPointerEnter={() => handleNodePointerEnter(node)}
                    onPointerMove={() => handleNodePointerEnter(node)}
                    onPointerLeave={handleNodePointerLeave}
                    onClick={(event) => handleNodeClick(node, event)}
                    onFocus={() => handleNodeFocus(node)}
                    onBlur={handleNodeBlur}
                    onKeyDown={(event) => handleNodeKeyDown(node, event)}
                    tabIndex={0}
                    role="button"
                    aria-pressed={selectedNodeId === node.id}
                    aria-label={`${node.name}${
                      node.record ? `, record ${node.record}` : ""
                    }`}
                    focusable="true"
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

        {cardNode && fighterMetadata && cardPosition ? (
          <div
            ref={(element) => {
              cardRef.current = element;
            }}
            style={{
              left: cardPosition.left,
              top: cardPosition.top,
            }}
            className="pointer-events-auto absolute z-30"
            onPointerEnter={() => {
              cardInteractionRef.current = true;
              clearHideTimer();
            }}
            onPointerLeave={() => {
              cardInteractionRef.current = false;
              if (!hoveredNodeRef.current && !selectedNodeRef.current) {
                scheduleCardClose();
              }
            }}
            onFocusCapture={() => {
              cardInteractionRef.current = true;
              clearHideTimer();
            }}
            onBlurCapture={(event) => {
              if (
                event.currentTarget.contains(
                  (event.relatedTarget as Node | null) ?? null,
                )
              ) {
                return;
              }
              cardInteractionRef.current = false;
              if (!hoveredNodeRef.current && !selectedNodeRef.current) {
                scheduleCardClose();
              }
            }}
          >
            <FighterInsightCard
              fighter={fighterMetadata}
              statusMessage={statusMessage}
              isLoading={detailsLoading}
              onOpenProfile={handleOpenProfile}
              onFilterDivision={handleFilterDivision}
              interactionMode={cardInteractionMode}
              registerCard={(element) => {
                cardRef.current = element;
              }}
            />
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
