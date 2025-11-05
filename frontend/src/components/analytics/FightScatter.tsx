"use client";

/**
 * High-Performance Fight Scatter Visualization Component
 * Displays fighter's fight history as a scatter plot with opponent headshots
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { scaleLinear, scaleTime } from "d3-scale";
import { zoom as d3Zoom, zoomIdentity, type D3ZoomEvent } from "d3-zoom";
import { quadtree, type Quadtree } from "d3-quadtree";
import { select } from "d3-selection";

import type {
  FightScatterProps,
  ScatterFight,
  Transform,
  TooltipState,
  TrendPoint,
  HexbinBucket,
  TrendWorkerRequest,
  TrendWorkerResponse,
} from "@/types/fight-scatter";
import {
  computeDomain,
  generateMonthlyTicks,
  getFirstFightYear,
} from "@/lib/fight-scatter-utils";
import { imageCache } from "@/lib/utils/imageCache";
import { FightTooltip } from "./FightTooltip";

// Visual configuration constants
const VISUAL_CONFIG = {
  MARKER_SIZE: 40,
  BORDER_WIDTH: 2,
  BADGE_SIZE: 12,
  COLORS: {
    WIN: "#2ecc71",
    LOSS: "#e74c3c",
    DRAW: "#95a5a6",
    TREND: "rgba(52, 152, 219, 0.6)",
    HEATMAP_COOL: "rgba(52, 152, 219, 0)",
    HEATMAP_WARM: "rgba(231, 76, 60, 0.4)",
  },
  FILTER_OPACITY: 0.15,
  ZOOM_EXTENT: [0.5, 5] as [number, number],
  ANIMATION_DURATION: 200,
  HIT_TEST_RADIUS: 25,
} as const;

const METHOD_ABBREV = {
  KO: "KO",
  SUB: "SUB",
  DEC: "DEC",
  OTHER: "?",
} as const;

/**
 * Formats opponent name to "F. LastName" format
 * Example: "Jon Jones" → "J. Jones"
 */
function formatOpponentName(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 0) return "";
  if (parts.length === 1) return parts[0]; // Single name

  const firstName = parts[0];
  const lastName = parts.slice(1).join(" ");
  return `${firstName.charAt(0)}. ${lastName}`;
}

/**
 * Extended fight interface with screen coordinates
 */
interface RenderedFight extends ScatterFight {
  screenX: number;
  screenY: number;
}

export function FightScatter({
  fights,
  hexbins,
  domainY,
  showDensity = false,
  showTrend = false,
  filterResults = [],
  filterMethods = [],
  onSelectFight,
  className = "",
  height = 600,
}: FightScatterProps) {
  // Canvas refs
  const containerRef = useRef<HTMLDivElement>(null);
  const heatmapCanvasRef = useRef<HTMLCanvasElement>(null);
  const pointsCanvasRef = useRef<HTMLCanvasElement>(null);
  const overlayRef = useRef<SVGSVGElement>(null);

  // State
  const [dimensions, setDimensions] = useState({ width: 800, height });
  const [transform, setTransform] = useState<Transform>({
    scale: 1,
    translateX: 0,
    translateY: 0,
  });
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const [trendPoints, setTrendPoints] = useState<TrendPoint[]>([]);
  const [imagesLoaded, setImagesLoaded] = useState(false);

  // Worker ref
  const workerRef = useRef<Worker | null>(null);

  // Compute domain
  const domain = useMemo(() => {
    const computed = computeDomain(fights);
    return {
      ...computed,
      yMin: domainY ? domainY[0] : computed.yMin,
      yMax: domainY ? domainY[1] : computed.yMax,
    };
  }, [fights, domainY]);

  // Create scales
  const xScale = useMemo(
    () =>
      scaleTime()
        .domain([new Date(domain.xMin), new Date(domain.xMax)])
        .range([40, dimensions.width - 40]),
    [domain.xMin, domain.xMax, dimensions.width]
  );

  const yScale = useMemo(
    () =>
      scaleLinear()
        .domain([domain.yMax, domain.yMin]) // Inverted: lower time at top
        .range([40, dimensions.height - 40]),
    [domain.yMin, domain.yMax, dimensions.height]
  );

  // Compute rendered fights with screen coordinates
  const renderedFights = useMemo(() => {
    return fights.map((fight) => {
      const date = new Date(fight.date);
      const baseX = xScale(date) || 0;
      const baseY = yScale(fight.finish_seconds) || 0;

      return {
        ...fight,
        screenX: baseX * transform.scale + transform.translateX,
        screenY: baseY * transform.scale + transform.translateY,
      };
    });
  }, [fights, xScale, yScale, transform]);

  // Build quadtree for hit-testing
  const quadTree = useMemo<Quadtree<RenderedFight>>(() => {
    return quadtree<RenderedFight>()
      .x((d) => d.screenX)
      .y((d) => d.screenY)
      .addAll(renderedFights);
  }, [renderedFights]);

  // Preload images and initials placeholders
  useEffect(() => {
    // Preload opponent images/placeholders
    const loadImages = async () => {
      const promises = fights.map((fight) => {
        if (fight.opponent_id) {
          return imageCache.getOpponentBitmap(
            fight.opponent_id,
            fight.headshot_url,
            fight.opponent_name
          );
        }
        return Promise.resolve(null);
      });

      await Promise.all(promises);
      setImagesLoaded(true);
    };

    loadImages();
  }, [fights]);

  // Initialize trend worker
  useEffect(() => {
    if (typeof Worker !== "undefined") {
      workerRef.current = new Worker(
        new URL("../../workers/trendWorker.ts", import.meta.url)
      );

      workerRef.current.addEventListener(
        "message",
        (event: MessageEvent<TrendWorkerResponse>) => {
          if (event.data.type === "result" && event.data.points) {
            setTrendPoints(event.data.points);
          }
        }
      );

      return () => {
        workerRef.current?.terminate();
      };
    }
  }, []);

  // Compute trend when enabled
  useEffect(() => {
    if (showTrend && workerRef.current && fights.length > 0) {
      const points: TrendPoint[] = fights.map((fight) => ({
        x: new Date(fight.date).getTime(),
        y: fight.finish_seconds,
      }));

      const request: TrendWorkerRequest = {
        type: "compute",
        points,
        windowSize: 7,
      };

      workerRef.current.postMessage(request);
    } else {
      setTrendPoints([]);
    }
  }, [showTrend, fights]);

  // Resize observer
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setDimensions({
          width: entry.contentRect.width,
          height,
        });
      }
    });

    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  }, [height]);

  // Set up zoom behavior
  useEffect(() => {
    const overlay = overlayRef.current;
    if (!overlay) return;

    const zoomBehavior = d3Zoom<SVGSVGElement, unknown>()
      .scaleExtent(VISUAL_CONFIG.ZOOM_EXTENT)
      .on("zoom", (event: D3ZoomEvent<SVGSVGElement, unknown>) => {
        const { k, x, y } = event.transform;
        setTransform({
          scale: k,
          translateX: x,
          translateY: y,
        });
      });

    const selection = select(overlay);
    selection.call(zoomBehavior);

    return () => {
      selection.on(".zoom", null);
    };
  }, []);

  // Render heatmap canvas
  useEffect(() => {
    if (!showDensity || !hexbins || hexbins.length === 0) {
      const canvas = heatmapCanvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
      }
      return;
    }

    const canvas = heatmapCanvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = dimensions.width * dpr;
    canvas.height = dimensions.height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, dimensions.width, dimensions.height);

    // Find max count for normalization
    const maxCount = Math.max(...hexbins.map((b) => b.count));

    // Render hexbins
    for (const bin of hexbins) {
      const alpha = Math.sqrt(bin.count / maxCount);
      ctx.fillStyle = `rgba(231, 76, 60, ${alpha * 0.4})`;

      // Simple square buckets (hexagons would be more complex)
      const bucketSize = 50;
      const x = bin.i * bucketSize;
      const y = bin.j * bucketSize;

      ctx.fillRect(x, y, bucketSize, bucketSize);
    }
  }, [showDensity, hexbins, dimensions]);

  // Render points canvas
  const renderPoints = useCallback(() => {
    const canvas = pointsCanvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = dimensions.width * dpr;
    canvas.height = dimensions.height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, dimensions.width, dimensions.height);

    // Check if filters are active
    const hasFilters =
      filterResults.length > 0 || filterMethods.length > 0;

    // Render each fight
    for (const fight of renderedFights) {
      const { screenX: x, screenY: y, result, method } = fight;

      // Check if fight matches filters
      const resultMatch =
        filterResults.length === 0 || filterResults.includes(result);
      const methodMatch =
        filterMethods.length === 0 || filterMethods.includes(method);
      const matches = resultMatch && methodMatch;

      // Determine opacity
      const opacity = hasFilters && !matches ? VISUAL_CONFIG.FILTER_OPACITY : 1;

      // Get image from cache (already preloaded with initials)
      const placeholderKey = fight.opponent_id ? `placeholder:${fight.opponent_id}` : "";
      const bitmap = imageCache.get(placeholderKey) || imageCache.get(fight.headshot_url || "");

      const radius = VISUAL_CONFIG.MARKER_SIZE / 2;

      ctx.save();
      ctx.globalAlpha = opacity;

      // Draw circular clip
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.clip();

      // Draw image or placeholder
      if (bitmap) {
        ctx.drawImage(
          bitmap,
          x - radius,
          y - radius,
          VISUAL_CONFIG.MARKER_SIZE,
          VISUAL_CONFIG.MARKER_SIZE
        );
      } else {
        // Fallback: gray circle
        ctx.fillStyle = "#95a5a6";
        ctx.fill();
      }

      ctx.restore();

      // Draw border
      ctx.save();
      ctx.globalAlpha = opacity;
      ctx.strokeStyle =
        result === "W"
          ? VISUAL_CONFIG.COLORS.WIN
          : result === "L"
            ? VISUAL_CONFIG.COLORS.LOSS
            : VISUAL_CONFIG.COLORS.DRAW;
      ctx.lineWidth = VISUAL_CONFIG.BORDER_WIDTH;
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();

      // Draw method badge
      if (method !== "OTHER") {
        const badgeSize = VISUAL_CONFIG.BADGE_SIZE;
        const badgeX = x + radius - badgeSize - 2;
        const badgeY = y - radius + 2;

        ctx.save();
        ctx.globalAlpha = opacity;
        ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
        ctx.fillRect(badgeX, badgeY, badgeSize, badgeSize);

        ctx.fillStyle = "#fff";
        ctx.font = "8px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(
          METHOD_ABBREV[method],
          badgeX + badgeSize / 2,
          badgeY + badgeSize / 2
        );
        ctx.restore();
      }

      // Draw opponent name label
      if (fight.opponent_name) {
        const label = formatOpponentName(fight.opponent_name);
        const labelY = y - radius - 8; // Position above circle

        ctx.save();
        ctx.globalAlpha = opacity;

        // Draw text shadow for readability
        ctx.shadowColor = "rgba(0, 0, 0, 0.8)";
        ctx.shadowBlur = 3;

        ctx.fillStyle = "#fff";
        ctx.font = "11px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";
        ctx.fillText(label, x, labelY);

        ctx.restore();
      }
    }

    // Render trend line
    if (showTrend && trendPoints.length > 1) {
      ctx.save();
      ctx.strokeStyle = VISUAL_CONFIG.COLORS.TREND;
      ctx.lineWidth = 2;
      ctx.beginPath();

      for (let i = 0; i < trendPoints.length; i++) {
        const point = trendPoints[i];
        const x = (xScale(new Date(point.x)) || 0) * transform.scale + transform.translateX;
        const y = (yScale(point.y) || 0) * transform.scale + transform.translateY;

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }

      ctx.stroke();
      ctx.restore();
    }
  }, [
    dimensions,
    renderedFights,
    filterResults,
    filterMethods,
    showTrend,
    trendPoints,
    xScale,
    yScale,
    transform,
  ]);

  // Re-render points when dependencies change
  useEffect(() => {
    renderPoints();
  }, [renderPoints]);

  // Handle pointer move (hover)
  const handlePointerMove = useCallback(
    (event: React.PointerEvent<SVGSVGElement>) => {
      const rect = overlayRef.current?.getBoundingClientRect();
      if (!rect) return;

      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;

      // Find nearest fight using quadtree
      const nearest = quadTree.find(x, y, VISUAL_CONFIG.HIT_TEST_RADIUS);

      if (nearest) {
        setTooltip({
          x: event.clientX,
          y: event.clientY,
          fight: nearest,
        });
      } else {
        setTooltip(null);
      }
    },
    [quadTree]
  );

  // Handle pointer leave
  const handlePointerLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  // Handle click
  const handleClick = useCallback(
    (event: React.MouseEvent<SVGSVGElement>) => {
      if (!onSelectFight) return;

      const rect = overlayRef.current?.getBoundingClientRect();
      if (!rect) return;

      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;

      const nearest = quadTree.find(x, y, VISUAL_CONFIG.HIT_TEST_RADIUS);

      if (nearest) {
        onSelectFight(nearest.id);
      }
    },
    [quadTree, onSelectFight]
  );

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {/* Canvas layers */}
      <div className="relative" style={{ width: "100%", height: `${height}px` }}>
        <canvas
          ref={heatmapCanvasRef}
          className="absolute left-0 top-0"
          style={{ width: "100%", height: "100%" }}
        />
        <canvas
          ref={pointsCanvasRef}
          className="absolute left-0 top-0"
          style={{ width: "100%", height: "100%" }}
        />

        {/* X-Axis Timeline */}
        <svg
          className="absolute left-0 top-0 pointer-events-none"
          style={{ width: "100%", height: "100%" }}
        >
          {/* Generate monthly tick marks */}
          {(() => {
            const ticks: JSX.Element[] = [];
            const startDate = new Date(domain.xMin);
            const endDate = new Date(domain.xMax);

            // Round to start of month
            const current = new Date(startDate.getFullYear(), startDate.getMonth(), 1);

            while (current <= endDate) {
              const x = (xScale(current) || 0) * transform.scale + transform.translateX;
              const month = current.getMonth();
              const year = current.getFullYear();

              // Determine tick hierarchy
              const isYearStart = month === 0;      // January
              const isQuarterly = month === 2 || month === 5 || month === 8; // Mar, Jun, Sep

              // Skip ticks that are outside visible area
              if (x >= 0 && x <= dimensions.width) {
                const tickHeight = isYearStart ? 12 : isQuarterly ? 8 : 5;
                const strokeWidth = isYearStart ? 2.5 : isQuarterly ? 1.8 : 1;
                const opacity = isYearStart ? 1 : isQuarterly ? 0.8 : 0.4;
                const yStart = dimensions.height - 30;

                ticks.push(
                  <g key={`tick-${year}-${month}`}>
                    <line
                      x1={x}
                      y1={yStart}
                      x2={x}
                      y2={yStart + tickHeight}
                      stroke="hsl(var(--border))"
                      strokeWidth={strokeWidth}
                      opacity={opacity}
                    />
                    {isYearStart && (
                      <text
                        x={x}
                        y={yStart + 22}
                        textAnchor="middle"
                        fill="hsl(var(--muted-foreground))"
                        fontSize={11}
                        fontWeight={500}
                      >
                        {year}
                      </text>
                    )}
                  </g>
                );
              }

              // Move to next month
              current.setMonth(current.getMonth() + 1);
            }

            return ticks;
          })()}
        </svg>

        <svg
          ref={overlayRef}
          className="absolute left-0 top-0 cursor-move"
          style={{ width: "100%", height: "100%" }}
          onPointerMove={handlePointerMove}
          onPointerLeave={handlePointerLeave}
          onClick={handleClick}
        />
      </div>

      {/* Tooltip */}
      {tooltip && (
        <FightTooltip fight={tooltip.fight} x={tooltip.x} y={tooltip.y} />
      )}

      {/* Loading indicator */}
      {!imagesLoaded && (
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-lg bg-gray-900/90 px-4 py-2 text-sm text-white">
          Loading images...
        </div>
      )}
    </div>
  );
}
