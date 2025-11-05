import React, {
  type CSSProperties,
  type MutableRefObject,
  type PointerEvent as ReactPointerEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { extent } from 'd3-array';
import { select } from 'd3-selection';
import { scaleLinear, scaleTime } from 'd3-scale';
import { quadtree, type Quadtree } from 'd3-quadtree';
import { zoom, zoomIdentity, type D3ZoomEvent, type ZoomTransform } from 'd3-zoom';

import { getOpponentBitmap } from '../../utils/imageCache';
import type { Fight, FightMethod, FightResult } from '../../types/fight';

/** Global constants controlling sizing, colors, and animation timings. */
const CANVAS_PADDING = { top: 32, right: 28, bottom: 56, left: 64 } as const;
const BASE_MARKER_SIZE = 40; // Render headshots at 40px (diameter) for clarity.
const HOVER_RING_EXTRA = 6; // Pixels added to radius when highlighting the hovered fight.
const FALLOUT_ALPHA = 0.15; // Opacity applied to fights filtered out by user selections.
const DENSITY_ALPHA_CAP = 0.75; // Clamp the heatmap alpha to prevent overwhelming the plot.
const ZOOM_MIN = 0.5;
const ZOOM_MAX = 12;
const DEFAULT_HEIGHT = 480;

const RESULT_BORDER_COLOR: Record<FightResult, string> = {
  W: '#2ecc71',
  L: '#e74c3c',
  D: '#95a5a6',
};

const METHOD_BADGE_COLOR: Record<FightMethod, string> = {
  KO: '#f39c12',
  SUB: '#8e44ad',
  DEC: '#2980b9',
  OTHER: '#7f8c8d',
};

const METHOD_BADGE_GLYPH: Record<FightMethod, string> = {
  KO: 'K',
  SUB: 'S',
  DEC: 'D',
  OTHER: 'O',
};

const FALLBACK_FILL_COLOR = '#2c3e50';
const TREND_LINE_COLOR = 'rgba(46, 204, 113, 0.65)';
const TREND_LINE_WIDTH = 2;
const TOOLTIP_BACKGROUND = 'rgba(12, 22, 34, 0.95)';
const TOOLTIP_BORDER = 'rgba(255, 255, 255, 0.08)';
const TOOLTIP_TEXT = '#f9fafb';
const TOGGLE_ACTIVE = '#1abc9c';
const TOGGLE_INACTIVE = '#34495e';

interface FightScatterProps {
  fights: Fight[];
  hexbins?: Array<{ i: number; j: number; count: number }>;
  domainY: [number, number];
  showDensity?: boolean;
  showTrend?: boolean;
  filterResults?: Array<FightResult>;
  filterMethods?: Array<FightMethod>;
  onSelectFight?: (id: string) => void;
}

interface FightWithDerived extends Fight {
  /** Cached Date object to avoid repeated parsing. */
  dateValue: Date;
  /** Indicates whether the fight passes the current result/method filters. */
  matchesFilters: boolean;
}

interface RenderableFight extends FightWithDerived {
  baseX: number;
  baseY: number;
  screenX: number;
  screenY: number;
  radius: number;
  isDimmed: boolean;
}

interface TooltipState {
  fight: RenderableFight;
  x: number;
  y: number;
}

type IdleHandle = number;

declare global {
  interface Window {
    requestIdleCallback?: (
      callback: IdleRequestCallback,
      options?: { timeout?: number },
    ) => IdleHandle;
    cancelIdleCallback?: (handle: IdleHandle) => void;
  }
}

/**
 * Polyfill-friendly helper for scheduling low-priority work without blocking rendering.
 */
const requestIdle = (callback: IdleRequestCallback): IdleHandle => {
  if (typeof window === 'undefined') {
    return 0;
  }
  if (window.requestIdleCallback) {
    return window.requestIdleCallback(callback, { timeout: 1500 });
  }
  return window.setTimeout(() => {
    const start = performance.now();
    callback({
      didTimeout: false,
      timeRemaining: () => Math.max(0, 16 - (performance.now() - start)),
    });
  }, 32);
};

/**
 * Clears an idle callback scheduled via {@link requestIdle}.
 */
const cancelIdle = (handle: IdleHandle): void => {
  if (typeof window === 'undefined' || !handle) {
    return;
  }
  if (window.cancelIdleCallback) {
    window.cancelIdleCallback(handle);
    return;
  }
  window.clearTimeout(handle);
};

/**
 * Lightweight in-memory representation of the density grid so we can memoize expensive
 * drawing operations and keep the main animation loop focused on marker rendering.
 */
interface DensityContext {
  canvas: OffscreenCanvas | null;
}

const useResizeObserver = (target: MutableRefObject<HTMLElement | null>): {
  width: number;
  height: number;
} => {
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const element = target.current;
    if (!element) {
      return;
    }
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect) {
          setDimensions({
            width: Math.floor(entry.contentRect.width),
            height: Math.floor(entry.contentRect.height),
          });
        }
      }
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [target]);

  return dimensions;
};

const FightScatter: React.FC<FightScatterProps> = ({
  fights,
  hexbins,
  domainY,
  showDensity = true,
  showTrend = true,
  filterResults,
  filterMethods,
  onSelectFight,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const heatmapCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const pointsCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const densityRef = useRef<DensityContext>({ canvas: null });
  const bitmapsRef = useRef<Map<string, ImageBitmap | null>>(new Map());
  const idleHandlesRef = useRef<Set<IdleHandle>>(new Set());
  const quadtreeRef = useRef<Quadtree<RenderableFight> | null>(null);
  const workerRef = useRef<Worker | null>(null);

  const [transform, setTransform] = useState<ZoomTransform>(zoomIdentity);
  const [densityEnabled, setDensityEnabled] = useState<boolean>(showDensity);
  const [trendEnabled, setTrendEnabled] = useState<boolean>(showTrend);
  const [trendLine, setTrendLine] = useState<Array<{ x: number; y: number }> | null>(null);
  const [hovered, setHovered] = useState<TooltipState | null>(null);
  const [bitmapVersion, setBitmapVersion] = useState<number>(0);

  useEffect(() => {
    setDensityEnabled(showDensity);
  }, [showDensity]);

  useEffect(() => {
    setTrendEnabled(showTrend);
  }, [showTrend]);

  const dimensions = useResizeObserver(containerRef);
  const height = dimensions.height || DEFAULT_HEIGHT;
  const width = dimensions.width || 0;
  const devicePixelRatio = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1;

  const fightsWithDerived = useMemo<Array<FightWithDerived>>(() => {
    return fights
      .map((fight) => {
        const dateValue = new Date(fight.date);
        const matchesResult =
          !filterResults || filterResults.length === 0 || filterResults.includes(fight.result);
        const matchesMethod =
          !filterMethods || filterMethods.length === 0 || filterMethods.includes(fight.method);
        return {
          ...fight,
          dateValue,
          matchesFilters: matchesResult && matchesMethod,
        };
      })
      .sort((a, b) => a.dateValue.getTime() - b.dateValue.getTime());
  }, [fights, filterMethods, filterResults]);

  const xDomain = useMemo<[Date, Date]>(() => {
    const computed = extent(fightsWithDerived, (fight) => fight.dateValue) as [Date, Date] | [];
    if (computed && computed[0] && computed[1]) {
      return computed;
    }
    const fallback = new Date();
    return [fallback, fallback];
  }, [fightsWithDerived]);

  const yDomain = useMemo<[number, number]>(() => domainY, [domainY]);

  const baseScales = useMemo(() => {
    if (!width || !height) {
      return null;
    }
    const xScale = scaleTime()
      .domain(xDomain)
      .range([CANVAS_PADDING.left, width - CANVAS_PADDING.right]);

    const yScale = scaleLinear()
      .domain(yDomain)
      .range([height - CANVAS_PADDING.bottom, CANVAS_PADDING.top]);

    return { xScale, yScale };
  }, [height, width, xDomain, yDomain]);

  const renderableFights = useMemo<Array<RenderableFight>>(() => {
    if (!baseScales) {
      return [];
    }
    const { xScale, yScale } = baseScales;
    const radius = BASE_MARKER_SIZE / 2;

    return fightsWithDerived.map((fight) => {
      const baseX = xScale(fight.dateValue);
      const baseY = yScale(fight.finish_seconds);
      const screenX = transform.applyX(baseX);
      const screenY = transform.applyY(baseY);
      const isDimmed = !fight.matchesFilters;
      return {
        ...fight,
        baseX,
        baseY,
        screenX,
        screenY,
        radius,
        isDimmed,
      };
    });
  }, [baseScales, fightsWithDerived, transform]);

  useEffect(() => {
    if (!renderableFights.length) {
      quadtreeRef.current = null;
      return;
    }
    const tree = quadtree<RenderableFight>()
      .x((fight) => fight.screenX)
      .y((fight) => fight.screenY);
    tree.addAll(renderableFights);
    quadtreeRef.current = tree;
  }, [renderableFights]);

  useEffect(() => {
    if (!overlayRef.current) {
      return;
    }
    const overlay = overlayRef.current;
    const zoomBehavior = zoom<HTMLDivElement, unknown>()
      .scaleExtent([ZOOM_MIN, ZOOM_MAX])
      .on('zoom', (event: D3ZoomEvent<HTMLDivElement, unknown>) => {
        setTransform(event.transform);
      });

    const selection = select(overlay);
    selection.call(zoomBehavior as any);

    return () => {
      selection.on('.zoom', null);
    };
  }, []);

  useEffect(() => {
    const overlay = overlayRef.current;
    if (!overlay) {
      return;
    }

    const handlePointerMove = (event: PointerEvent): void => {
      const rect = overlay.getBoundingClientRect();
      const pointerX = event.clientX - rect.left;
      const pointerY = event.clientY - rect.top;
      const tree = quadtreeRef.current;
      if (!tree) {
        setHovered(null);
        return;
      }
      const nearest = tree.find(pointerX, pointerY, BASE_MARKER_SIZE * 0.75);
      if (nearest && !nearest.isDimmed) {
        setHovered({ fight: nearest, x: pointerX, y: pointerY });
      } else {
        setHovered(null);
      }
    };

    const handlePointerLeave = (): void => {
      setHovered(null);
    };

    const handleClick = (event: PointerEvent): void => {
      const rect = overlay.getBoundingClientRect();
      const pointerX = event.clientX - rect.left;
      const pointerY = event.clientY - rect.top;
      const tree = quadtreeRef.current;
      if (!tree) {
        return;
      }
      const nearest = tree.find(pointerX, pointerY, BASE_MARKER_SIZE * 0.75);
      if (nearest && !nearest.isDimmed) {
        onSelectFight?.(nearest.id);
      }
    };

    overlay.addEventListener('pointermove', handlePointerMove);
    overlay.addEventListener('pointerleave', handlePointerLeave);
    overlay.addEventListener('click', handleClick);
    return () => {
      overlay.removeEventListener('pointermove', handlePointerMove);
      overlay.removeEventListener('pointerleave', handlePointerLeave);
      overlay.removeEventListener('click', handleClick);
    };
  }, [onSelectFight]);

  useEffect(() => {
    idleHandlesRef.current.forEach((handle) => cancelIdle(handle));
    idleHandlesRef.current.clear();

    if (!trendEnabled) {
      setTrendLine(null);
      return;
    }
    if (typeof window === 'undefined' || renderableFights.length === 0) {
      return;
    }

    if (!workerRef.current) {
      workerRef.current = new Worker(new URL('../../workers/trendWorker.ts', import.meta.url), {
        type: 'module',
      });
    }
    const worker = workerRef.current;
    const handleMessage = (event: MessageEvent<{ trend?: Array<{ x: number; y: number }> }>): void => {
      if (event.data?.trend) {
        setTrendLine(event.data.trend);
      }
    };
    worker.addEventListener('message', handleMessage);

    const points = renderableFights.map((fight) => ({
      x: fight.dateValue.getTime(),
      y: fight.finish_seconds,
    }));
    worker.postMessage({ points });

    return () => {
      worker.removeEventListener('message', handleMessage);
    };
  }, [renderableFights, trendEnabled]);

  useEffect(() => {
    const idleHandles = idleHandlesRef.current;
    return () => {
      workerRef.current?.terminate();
      workerRef.current = null;
      idleHandles.forEach((handle) => cancelIdle(handle));
      idleHandles.clear();
    };
  }, []);

  const scheduleBitmapPrefetch = useCallback(
    (fight: RenderableFight) => {
      if (typeof window === 'undefined') {
        return;
      }
      const cacheKey = fight.opponentId;
      if (bitmapsRef.current.has(cacheKey)) {
        return;
      }
      let handle: IdleHandle = 0;
      handle = requestIdle(() => {
        idleHandlesRef.current.delete(handle);
        getOpponentBitmap(cacheKey, fight.headshotUrl)
          .then((bitmap) => {
            bitmapsRef.current.set(cacheKey, bitmap);
            setBitmapVersion((value) => value + 1);
          })
          .catch(() => {
            bitmapsRef.current.set(cacheKey, null);
            setBitmapVersion((value) => value + 1);
          });
      });
      idleHandlesRef.current.add(handle);
    },
    [],
  );

  useEffect(() => {
    if (!renderableFights.length || !baseScales) {
      return;
    }
    const sorted = [...renderableFights].sort((a, b) => {
      const dx = a.screenX - (width / 2);
      const dy = a.screenY - (height / 2);
      const distanceA = Math.hypot(dx, dy);
      const dxB = b.screenX - (width / 2);
      const dyB = b.screenY - (height / 2);
      const distanceB = Math.hypot(dxB, dyB);
      return distanceA - distanceB;
    });

    sorted.slice(0, 64).forEach((fight) => {
      scheduleBitmapPrefetch(fight);
    });
  }, [baseScales, height, renderableFights, scheduleBitmapPrefetch, transform, width]);

  const drawDensityLayer = useCallback(() => {
    const canvas = heatmapCanvasRef.current;
    if (!canvas) {
      return;
    }
    const context = canvas.getContext('2d');
    if (!context) {
      return;
    }

    const widthPx = width;
    const heightPx = height;

    canvas.width = widthPx * devicePixelRatio;
    canvas.height = heightPx * devicePixelRatio;
    canvas.style.width = `${widthPx}px`;
    canvas.style.height = `${heightPx}px`;

    context.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    context.clearRect(0, 0, widthPx, heightPx);

    if (!densityEnabled || !hexbins?.length || !baseScales) {
      return;
    }

    const offscreenCanvas = typeof OffscreenCanvas !== 'undefined' ? densityRef.current.canvas ?? new OffscreenCanvas(widthPx * devicePixelRatio, heightPx * devicePixelRatio) : null;
    if (offscreenCanvas && offscreenCanvas !== densityRef.current.canvas) {
      densityRef.current.canvas = offscreenCanvas;
    }
    const targetContext = offscreenCanvas?.getContext('2d') ?? context;
    if (!targetContext) {
      return;
    }
    if (offscreenCanvas) {
      if (offscreenCanvas.width !== widthPx * devicePixelRatio || offscreenCanvas.height !== heightPx * devicePixelRatio) {
        offscreenCanvas.width = widthPx * devicePixelRatio;
        offscreenCanvas.height = heightPx * devicePixelRatio;
      }
      targetContext.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
      targetContext.clearRect(0, 0, widthPx, heightPx);
    }

    const { xScale, yScale } = baseScales;
    const maxI = hexbins.reduce((max, bin) => Math.max(max, bin.i), 0);
    const maxJ = hexbins.reduce((max, bin) => Math.max(max, bin.j), 0);
    const maxCount = hexbins.reduce((max, bin) => Math.max(max, bin.count), 0) || 1;
    const domainXStart = xScale.domain()[0].getTime();
    const domainXEnd = xScale.domain()[1].getTime();
    const domainYStart = yScale.domain()[0];
    const domainYEnd = yScale.domain()[1];
    const binWidthMs = (domainXEnd - domainXStart) / (maxI + 1);
    const binHeightVal = (domainYEnd - domainYStart) / (maxJ + 1);

    hexbins.forEach((bin) => {
      const startTime = domainXStart + bin.i * binWidthMs;
      const endTime = domainXStart + (bin.i + 1) * binWidthMs;
      const startVal = domainYStart + bin.j * binHeightVal;
      const endVal = domainYStart + (bin.j + 1) * binHeightVal;

      const x0 = transform.applyX(xScale(new Date(startTime)));
      const x1 = transform.applyX(xScale(new Date(endTime)));
      const y0 = transform.applyY(yScale(startVal));
      const y1 = transform.applyY(yScale(endVal));

      const rectX = Math.min(x0, x1);
      const rectY = Math.min(y0, y1);
      const rectWidth = Math.abs(x1 - x0);
      const rectHeight = Math.abs(y1 - y0);

      const intensity = Math.sqrt(bin.count / maxCount) * DENSITY_ALPHA_CAP;
      targetContext.fillStyle = `rgba(52, 152, 219, ${intensity.toFixed(3)})`;
      targetContext.fillRect(rectX, rectY, rectWidth, rectHeight);
    });

    if (offscreenCanvas) {
      context.drawImage(offscreenCanvas, 0, 0, widthPx, heightPx);
    }
  }, [baseScales, densityEnabled, devicePixelRatio, hexbins, height, transform, width]);

  const drawPointsLayer = useCallback(() => {
    const canvas = pointsCanvasRef.current;
    if (!canvas) {
      return;
    }
    const context = canvas.getContext('2d');
    if (!context) {
      return;
    }

    const widthPx = width;
    const heightPx = height;

    canvas.width = widthPx * devicePixelRatio;
    canvas.height = heightPx * devicePixelRatio;
    canvas.style.width = `${widthPx}px`;
    canvas.style.height = `${heightPx}px`;

    context.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    context.clearRect(0, 0, widthPx, heightPx);

    renderableFights.forEach((fight) => {
      const { screenX, screenY, radius, result, method, isDimmed, opponentId } = fight;
      const opacity = isDimmed ? FALLOUT_ALPHA : 1;
      context.globalAlpha = opacity;
      const bitmap = bitmapsRef.current.get(opponentId ?? fight.id);

      const borderColor = RESULT_BORDER_COLOR[result];
      context.lineWidth = 2;
      context.strokeStyle = borderColor;

      if (bitmap) {
        context.save();
        context.beginPath();
        context.arc(screenX, screenY, radius, 0, Math.PI * 2);
        context.closePath();
        context.clip();
        context.drawImage(bitmap, screenX - radius, screenY - radius, radius * 2, radius * 2);
        context.restore();
      } else {
        context.beginPath();
        context.arc(screenX, screenY, radius, 0, Math.PI * 2);
        context.closePath();
        context.fillStyle = METHOD_BADGE_COLOR[method] ?? FALLBACK_FILL_COLOR;
        context.fill();
      }

      context.beginPath();
      context.arc(screenX, screenY, radius, 0, Math.PI * 2);
      context.stroke();

      const badgeRadius = radius * 0.35;
      const badgeX = screenX + radius * 0.6;
      const badgeY = screenY - radius * 0.6;
      context.beginPath();
      context.fillStyle = METHOD_BADGE_COLOR[method];
      context.arc(badgeX, badgeY, badgeRadius, 0, Math.PI * 2);
      context.fill();
      context.font = `${Math.max(8, badgeRadius * 1.8)}px "Inter", sans-serif`;
      context.fillStyle = '#ffffff';
      context.textAlign = 'center';
      context.textBaseline = 'middle';
      context.fillText(METHOD_BADGE_GLYPH[method], badgeX, badgeY + 0.5);

      if (hovered?.fight.id === fight.id) {
        context.globalAlpha = 1;
        context.beginPath();
        context.lineWidth = 2;
        context.strokeStyle = '#ecf0f1';
        context.arc(screenX, screenY, radius + HOVER_RING_EXTRA, 0, Math.PI * 2);
        context.stroke();
      }
    });

    context.globalAlpha = 1;

    if (trendEnabled && trendLine && baseScales) {
      context.beginPath();
      context.lineWidth = TREND_LINE_WIDTH;
      context.strokeStyle = TREND_LINE_COLOR;

      trendLine.forEach((point, index) => {
        const baseX = baseScales.xScale(new Date(point.x));
        const baseY = baseScales.yScale(point.y);
        const x = transform.applyX(baseX);
        const y = transform.applyY(baseY);
        if (index === 0) {
          context.moveTo(x, y);
        } else {
          context.lineTo(x, y);
        }
      });
      context.stroke();
    }
  }, [baseScales, devicePixelRatio, hovered, renderableFights, trendEnabled, trendLine, transform, width, height]);

  useEffect(() => {
    drawDensityLayer();
  }, [drawDensityLayer]);

  useEffect(() => {
    drawPointsLayer();
  }, [drawPointsLayer, bitmapVersion]);

  const tooltipStyle: CSSProperties = useMemo(() => {
    if (!hovered) {
      return { display: 'none' };
    }
    return {
      position: 'absolute',
      pointerEvents: 'none',
      transform: 'translate(-50%, -110%)',
      left: hovered.x,
      top: hovered.y,
      background: TOOLTIP_BACKGROUND,
      color: TOOLTIP_TEXT,
      borderRadius: 8,
      border: `1px solid ${TOOLTIP_BORDER}`,
      padding: '12px 16px',
      fontSize: 12,
      maxWidth: 260,
      boxShadow: '0 12px 24px rgba(0,0,0,0.35)',
    };
  }, [hovered]);

  const renderTooltipContent = (): React.ReactNode => {
    if (!hovered) {
      return null;
    }
    const { fight } = hovered;
    const finishMinutes = Math.floor(fight.finish_seconds / 60);
    const finishSeconds = Math.round(fight.finish_seconds % 60)
      .toString()
      .padStart(2, '0');
    const finishDisplay = `${finishMinutes}:${finishSeconds}`;
    const roundTime = fight.finishRoundTime ?? finishDisplay;

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <span style={{ fontWeight: 600 }}>{fight.opponentName ?? 'Opponent TBD'}</span>
        <span style={{ opacity: 0.8 }}>{fight.eventName ?? 'Event Unknown'}</span>
        <span>
          {fight.method} • {fight.result} • Round {fight.finishRound ?? '?'} @ {roundTime}
        </span>
        {fight.ufcStatsUrl ? (
          <a
            href={fight.ufcStatsUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: '#1abc9c', textDecoration: 'underline', marginTop: 4 }}
          >
            View on UFCStats
          </a>
        ) : null}
      </div>
    );
  };

  const handleToggleClick = (type: 'density' | 'trend') => (event: ReactPointerEvent<HTMLButtonElement>) => {
    event.preventDefault();
    if (type === 'density') {
      setDensityEnabled((value) => !value);
    } else {
      setTrendEnabled((value) => !value);
    }
  };

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: DEFAULT_HEIGHT,
        background: '#0b1622',
        borderRadius: 16,
        padding: 12,
        boxShadow: '0 32px 80px rgba(0,0,0,0.35)',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
        <button
          type="button"
          onClick={handleToggleClick('density')}
          style={{
            padding: '6px 12px',
            borderRadius: 999,
            border: 'none',
            cursor: 'pointer',
            background: densityEnabled ? TOGGLE_ACTIVE : TOGGLE_INACTIVE,
            color: '#ecf0f1',
            fontWeight: 600,
            letterSpacing: 0.3,
          }}
        >
          Density
        </button>
        <button
          type="button"
          onClick={handleToggleClick('trend')}
          style={{
            padding: '6px 12px',
            borderRadius: 999,
            border: 'none',
            cursor: 'pointer',
            background: trendEnabled ? TOGGLE_ACTIVE : TOGGLE_INACTIVE,
            color: '#ecf0f1',
            fontWeight: 600,
            letterSpacing: 0.3,
          }}
        >
          Trend
        </button>
      </div>
      <div style={{ position: 'relative', flex: 1 }}>
        <canvas ref={heatmapCanvasRef} style={{ position: 'absolute', inset: 0 }} />
        <canvas ref={pointsCanvasRef} style={{ position: 'absolute', inset: 0 }} />
        <div
          ref={overlayRef}
          style={{
            position: 'absolute',
            inset: 0,
            touchAction: 'none',
          }}
        />
        <div style={tooltipStyle}>{renderTooltipContent()}</div>
      </div>
    </div>
  );
};

export default FightScatter;
