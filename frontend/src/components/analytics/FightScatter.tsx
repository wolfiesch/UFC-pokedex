import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { scaleLinear, scaleSqrt, scaleTime } from 'd3-scale';
import { extent, max } from 'd3-array';
import { quadtree, type Quadtree } from 'd3-quadtree';
import { zoom, zoomIdentity, type D3ZoomEvent, type ZoomTransform } from 'd3-zoom';
import { select } from 'd3-selection';
import { pointer as pointerEvent } from 'd3-selection';
import clsx from 'clsx';

import type { Fight, HexBinCell } from '../../types/fight';
import { Button } from '../ui/button';
import {
  cancelIdleCallbackShim,
  getOpponentBitmap,
  requestIdleCallbackShim,
  type IdleCallbackHandle,
} from '../../utils/imageCache';

const RESULT_BORDER: Record<Fight['result'], string> = {
  W: '#2ecc71',
  L: '#e74c3c',
  D: '#95a5a6',
};

const RESULT_FALLBACK_FILL: Record<Fight['result'], string> = {
  W: '#eafaf1',
  L: '#fdecea',
  D: '#ecf0f1',
};

const METHOD_BADGE_COLOR: Record<Fight['method'], string> = {
  KO: '#f1c40f',
  SUB: '#8e44ad',
  DEC: '#2980b9',
  OTHER: '#7f8c8d',
};

const METHOD_BADGE_LABEL: Record<Fight['method'], string> = {
  KO: 'KO',
  SUB: 'SUB',
  DEC: 'DEC',
  OTHER: 'OTH',
};

const DIMMED_ALPHA = 0.15;
const HOVER_ALPHA = 0.85;
const SELECTED_SCALE = 1.15;
const DEFAULT_MARKER_SIZE = 40; // px
const MIN_MARKER_SIZE = 32;
const MAX_MARKER_SIZE = 48;
const MARKER_BORDER = 2;
const BADGE_SIZE = 12;
const BADGE_RADIUS = 4;
const TREND_LINE_COLOR = 'rgba(52, 152, 219, 0.6)';
const TREND_LINE_WIDTH = 2;
const DENSITY_ALPHA_MAX = 0.32;
const ZOOM_SCALE_EXTENT: [number, number] = [0.75, 12];
const PADDING = { top: 32, right: 28, bottom: 48, left: 56 } as const;
const MIN_CANVAS_HEIGHT = 360;

const HEXBIN_OFFSET = 0.5; // positions cells at bucket centers

interface PreparedFight {
  fight: Fight;
  dateValue: number;
  finishSeconds: number;
  isDimmed: boolean;
}

interface RenderableFight extends PreparedFight {
  xPixel: number;
  yPixel: number;
}

interface TooltipState {
  fight: Fight;
  position: { x: number; y: number };
}

interface FightScatterProps {
  fights: Fight[];
  hexbins?: HexBinCell[];
  domainY: [number, number];
  showDensity?: boolean;
  showTrend?: boolean;
  filterResults?: Fight['result'][];
  filterMethods?: Fight['method'][];
  onSelectFight?: (id: string) => void;
}

const clampMarkerSize = (size: number) =>
  Math.min(MAX_MARKER_SIZE, Math.max(MIN_MARKER_SIZE, size));

const getCanvasSize = (element: HTMLDivElement | null): { width: number; height: number } => {
  if (!element) {
    return { width: 0, height: 0 };
  }
  const { width, height } = element.getBoundingClientRect();
  return {
    width,
    height: Math.max(height, MIN_CANVAS_HEIGHT),
  };
};

const methodBadgeFont = () => '8px var(--font-sans, "Inter", sans-serif)';

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
  const pointsCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const heatmapCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const heatmapCtxRef = useRef<CanvasRenderingContext2D | null>(null);
  const pointsCtxRef = useRef<CanvasRenderingContext2D | null>(null);
  const densityOffscreenRef = useRef<OffscreenCanvas | HTMLCanvasElement | null>(null);
  const densityOffscreenCtxRef =
    useRef<OffscreenCanvasRenderingContext2D | CanvasRenderingContext2D | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const hoverIdRef = useRef<string | null>(null);
  const selectedIdRef = useRef<string | null>(null);
  const transformRef = useRef<ZoomTransform>(zoomIdentity);
  const quadtreeRef = useRef<Quadtree<RenderableFight> | null>(null);
  const bitmapsRef = useRef<Map<string, ImageBitmap>>(new Map());
  const trendWorkerRef = useRef<Worker | null>(null);
  const idleHandleRef = useRef<IdleCallbackHandle | null>(null);
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({ width: 0, height: MIN_CANVAS_HEIGHT });
  const [densityEnabled, setDensityEnabled] = useState(showDensity);
  const [trendEnabled, setTrendEnabled] = useState(showTrend);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const [trendLine, setTrendLine] = useState<{ x: number; y: number }[]>([]);

  useEffect(() => {
    setDensityEnabled(showDensity);
  }, [showDensity]);

  useEffect(() => {
    setTrendEnabled(showTrend);
  }, [showTrend]);

  const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1;

  const dateExtent = useMemo(() => {
    const ext = extent(fights, (fight) => new Date(fight.date).getTime());
    if (!ext[0] || !ext[1]) {
      const now = Date.now();
      return [now - 1000 * 60 * 60 * 24 * 30, now] as [number, number];
    }
    return ext as [number, number];
  }, [fights]);

  const preparedFights = useMemo<PreparedFight[]>(() => {
    const resultsActive = Boolean(filterResults?.length);
    const methodsActive = Boolean(filterMethods?.length);

    return fights
      .map((fight) => {
        const dateValue = new Date(fight.date).getTime();
        const finishSeconds = fight.finish_seconds;
        const dimResult = resultsActive && !filterResults!.includes(fight.result);
        const dimMethod = methodsActive && !filterMethods!.includes(fight.method);
        return {
          fight,
          dateValue,
          finishSeconds,
          isDimmed: dimResult || dimMethod,
        };
      })
      .sort((a, b) => a.dateValue - b.dateValue);
  }, [fights, filterMethods, filterResults]);

  const xScale = useMemo(() => {
    return scaleTime<number, number>()
      .domain([new Date(dateExtent[0]), new Date(dateExtent[1])])
      .range([PADDING.left, Math.max(PADDING.left + 1, dimensions.width - PADDING.right)]);
  }, [dateExtent, dimensions.width]);

  const yScale = useMemo(() => {
    return scaleLinear()
      .domain(domainY)
      .range([Math.max(PADDING.top + 1, dimensions.height - PADDING.bottom), PADDING.top])
      .nice();
  }, [dimensions.height, domainY]);

  const renderableFights = useMemo<RenderableFight[]>(() => {
    return preparedFights.map((item) => ({
      ...item,
      xPixel: xScale(new Date(item.dateValue)),
      yPixel: yScale(item.finishSeconds),
    }));
  }, [preparedFights, xScale, yScale]);

  useEffect(() => {
    if (renderableFights.length === 0) {
      quadtreeRef.current = null;
      return;
    }
    const tree = quadtree<RenderableFight>()
      .x((d) => d.xPixel)
      .y((d) => d.yPixel);
    tree.addAll(renderableFights);
    quadtreeRef.current = tree;
  }, [renderableFights]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return undefined;
    }

    const observer = new ResizeObserver(() => {
      setDimensions(getCanvasSize(container));
    });
    observer.observe(container);
    setDimensions(getCanvasSize(container));

    return () => {
      observer.disconnect();
    };
  }, []);

  useEffect(() => {
    const pointsCanvas = pointsCanvasRef.current;
    const heatCanvas = heatmapCanvasRef.current;
    if (!pointsCanvas || !heatCanvas) {
      return;
    }

    const resizeCanvas = (canvas: HTMLCanvasElement) => {
      canvas.width = Math.floor(dimensions.width * dpr);
      canvas.height = Math.floor(dimensions.height * dpr);
      canvas.style.width = `${dimensions.width}px`;
      canvas.style.height = `${dimensions.height}px`;
    };

    resizeCanvas(pointsCanvas);
    resizeCanvas(heatCanvas);

    pointsCtxRef.current = pointsCanvas.getContext('2d');
    heatmapCtxRef.current = heatCanvas.getContext('2d');

    if (typeof window !== 'undefined') {
      const offscreenWidth = Math.floor(dimensions.width * dpr);
      const offscreenHeight = Math.floor(dimensions.height * dpr);
      if (typeof OffscreenCanvas !== 'undefined') {
        const offscreen = new OffscreenCanvas(offscreenWidth, offscreenHeight);
        densityOffscreenRef.current = offscreen;
        densityOffscreenCtxRef.current = offscreen.getContext('2d');
      } else {
        const fallback = document.createElement('canvas');
        fallback.width = offscreenWidth;
        fallback.height = offscreenHeight;
        densityOffscreenRef.current = fallback;
        densityOffscreenCtxRef.current = fallback.getContext('2d');
      }
    }
  }, [dimensions.height, dimensions.width, dpr]);

  const renderDensityLayer = useCallback(
    (transform: ZoomTransform) => {
      const mainCtx = heatmapCtxRef.current;
      if (!mainCtx) {
        return;
      }
      const offscreenCanvas = densityOffscreenRef.current;
      const offscreenCtx = densityOffscreenCtxRef.current ?? null;

      mainCtx.save();
      mainCtx.setTransform(1, 0, 0, 1, 0, 0);
      mainCtx.clearRect(0, 0, mainCtx.canvas.width, mainCtx.canvas.height);
      mainCtx.restore();

      if (!densityEnabled || !hexbins || hexbins.length === 0) {
        return;
      }

      if (offscreenCtx && offscreenCanvas) {
        offscreenCtx.save();
        offscreenCtx.setTransform(1, 0, 0, 1, 0, 0);
        offscreenCtx.clearRect(0, 0, offscreenCanvas.width, offscreenCanvas.height);
        offscreenCtx.restore();
      }

      const maxCount = max(hexbins, (cell) => cell.count) ?? 0;
      if (maxCount === 0) {
        return;
      }

      const alphaScale = scaleSqrt().domain([0, maxCount]).range([0, DENSITY_ALPHA_MAX]);
      const [minTime, maxTime] = dateExtent;
      const timeSpan = Math.max(1, maxTime - minTime);
      const [minFinish, maxFinish] = domainY;
      const finishSpan = Math.max(1, maxFinish - minFinish);
      const maxI = max(hexbins, (cell) => cell.i) ?? 0;
      const maxJ = max(hexbins, (cell) => cell.j) ?? 0;
      const binTime = timeSpan / Math.max(1, maxI + 1);
      const binFinish = finishSpan / Math.max(1, maxJ + 1);

      const drawCtx = offscreenCtx ?? mainCtx;

      drawCtx.save();
      drawCtx.scale(dpr, dpr);
      drawCtx.globalCompositeOperation = 'source-over';
      drawCtx.globalAlpha = 1;

      hexbins.forEach((cell) => {
        const centerTime = minTime + (cell.i + HEXBIN_OFFSET) * binTime;
        const centerFinish = minFinish + (cell.j + HEXBIN_OFFSET) * binFinish;

        const baseX = xScale(new Date(centerTime));
        const baseY = yScale(centerFinish);
        const halfWidth = (xScale(new Date(centerTime + binTime / 2)) - xScale(new Date(centerTime - binTime / 2))) / 2;
        const halfHeight =
          (yScale(centerFinish - binFinish / 2) - yScale(centerFinish + binFinish / 2)) / 2;

        const x0 = transform.applyX(baseX - halfWidth);
        const x1 = transform.applyX(baseX + halfWidth);
        const y0 = transform.applyY(baseY - halfHeight);
        const y1 = transform.applyY(baseY + halfHeight);

        const width = Math.abs(x1 - x0);
        const height = Math.abs(y1 - y0);
        const rectX = Math.min(x0, x1);
        const rectY = Math.min(y0, y1);

        if (!Number.isFinite(width) || !Number.isFinite(height)) {
          return;
        }

        drawCtx.fillStyle = `rgba(52, 73, 94, ${alphaScale(cell.count).toFixed(3)})`;
        drawCtx.fillRect(rectX, rectY, width, height);
      });

      drawCtx.restore();

      if (drawCtx !== mainCtx && offscreenCanvas) {
        mainCtx.drawImage(offscreenCanvas as unknown as CanvasImageSource, 0, 0);
      }
    },
    [dateExtent, densityEnabled, domainY, dpr, hexbins, xScale, yScale],
  );

  const drawPoints = useCallback(() => {
    const ctx = pointsCtxRef.current;
    if (!ctx) {
      return;
    }

    const { width, height } = ctx.canvas;
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.restore();

    const transform = transformRef.current;
    renderDensityLayer(transform);

    const hoveredId = hoverIdRef.current;
    const selectedId = selectedIdRef.current;

    ctx.save();
    ctx.scale(dpr, dpr);

    renderableFights.forEach((item) => {
      const { fight, isDimmed, xPixel, yPixel } = item;
      const canvasX = transform.applyX(xPixel);
      const canvasY = transform.applyY(yPixel);

      if (
        canvasX < PADDING.left - MAX_MARKER_SIZE ||
        canvasX > dimensions.width - PADDING.right + MAX_MARKER_SIZE ||
        canvasY < PADDING.top - MAX_MARKER_SIZE ||
        canvasY > dimensions.height - PADDING.bottom + MAX_MARKER_SIZE
      ) {
        return;
      }

      const borderColor = RESULT_BORDER[fight.result];
      const fallbackFill = RESULT_FALLBACK_FILL[fight.result];
      const bitmap = bitmapsRef.current.get(fight.opponentId);
      const highlightScale = selectedId === fight.id ? SELECTED_SCALE : 1;
      const hoverScale = hoveredId === fight.id ? 1.05 : 1;
      const size = clampMarkerSize(DEFAULT_MARKER_SIZE * highlightScale * hoverScale);
      const radius = size / 2;
      const borderWidth = MARKER_BORDER;
      const alpha = isDimmed ? DIMMED_ALPHA : hoveredId && hoveredId !== fight.id ? HOVER_ALPHA : 1;

      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.beginPath();
      ctx.arc(canvasX, canvasY, radius, 0, Math.PI * 2);
      ctx.closePath();
      ctx.fillStyle = fallbackFill;
      ctx.fill();

      if (bitmap) {
        ctx.save();
        ctx.clip();
        ctx.drawImage(bitmap, canvasX - radius, canvasY - radius, radius * 2, radius * 2);
        ctx.restore();
      }

      ctx.lineWidth = borderWidth;
      ctx.strokeStyle = borderColor;
      ctx.stroke();
      ctx.restore();

      // Method badge overlay
      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.fillStyle = METHOD_BADGE_COLOR[fight.method];
      const badgeWidth = BADGE_SIZE;
      const badgeHeight = BADGE_SIZE;
      const badgeX = canvasX + radius * 0.45 - badgeWidth;
      const badgeY = canvasY - radius * 0.9;
      ctx.beginPath();
      ctx.moveTo(badgeX + BADGE_RADIUS, badgeY);
      ctx.lineTo(badgeX + badgeWidth - BADGE_RADIUS, badgeY);
      ctx.quadraticCurveTo(badgeX + badgeWidth, badgeY, badgeX + badgeWidth, badgeY + BADGE_RADIUS);
      ctx.lineTo(badgeX + badgeWidth, badgeY + badgeHeight - BADGE_RADIUS);
      ctx.quadraticCurveTo(
        badgeX + badgeWidth,
        badgeY + badgeHeight,
        badgeX + badgeWidth - BADGE_RADIUS,
        badgeY + badgeHeight,
      );
      ctx.lineTo(badgeX + BADGE_RADIUS, badgeY + badgeHeight);
      ctx.quadraticCurveTo(badgeX, badgeY + badgeHeight, badgeX, badgeY + badgeHeight - BADGE_RADIUS);
      ctx.lineTo(badgeX, badgeY + BADGE_RADIUS);
      ctx.quadraticCurveTo(badgeX, badgeY, badgeX + BADGE_RADIUS, badgeY);
      ctx.closePath();
      ctx.fill();

      ctx.fillStyle = '#ffffff';
      ctx.font = methodBadgeFont();
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(METHOD_BADGE_LABEL[fight.method], badgeX + badgeWidth / 2, badgeY + badgeHeight / 2 + 1);
      ctx.restore();
    });

    if (trendEnabled && trendLine.length > 0) {
      ctx.save();
      ctx.globalAlpha = 1;
      ctx.lineWidth = TREND_LINE_WIDTH;
      ctx.strokeStyle = TREND_LINE_COLOR;
      ctx.beginPath();
      trendLine.forEach((point, index) => {
        const baseX = xScale(new Date(point.x));
        const baseY = yScale(point.y);
        const canvasX = transform.applyX(baseX);
        const canvasY = transform.applyY(baseY);
        if (index === 0) {
          ctx.moveTo(canvasX, canvasY);
        } else {
          ctx.lineTo(canvasX, canvasY);
        }
      });
      ctx.stroke();
      ctx.restore();
    }

    ctx.restore();
  }, [
    dpr,
    dimensions.height,
    dimensions.width,
    renderDensityLayer,
    renderableFights,
    trendEnabled,
    trendLine,
    xScale,
    yScale,
  ]);

  const scheduleDraw = useCallback(() => {
    if (animationFrameRef.current !== null) {
      return;
    }
    animationFrameRef.current = requestAnimationFrame(() => {
      animationFrameRef.current = null;
      drawPoints();
    });
  }, [drawPoints]);

  const ensureBitmap = useCallback(
    (item: PreparedFight) => {
      const { fight } = item;
      if (!fight.headshotUrl) {
        return;
      }
      if (bitmapsRef.current.has(fight.opponentId)) {
        return;
      }

      getOpponentBitmap(fight.opponentId, fight.headshotUrl)
        .then((bitmap) => {
          bitmapsRef.current.set(fight.opponentId, bitmap);
          scheduleDraw();
        })
        .catch(() => {
          // Ignore headshot failures; fallback styling will kick in.
        });
    },
    [scheduleDraw],
  );

  useEffect(() => {
    if (idleHandleRef.current) {
      cancelIdleCallbackShim(idleHandleRef.current);
      idleHandleRef.current = null;
    }

    if (preparedFights.length === 0) {
      return undefined;
    }

    const queue = [...preparedFights];

    const processQueue: IdleRequestCallback = (deadline) => {
      while (queue.length > 0 && (deadline.timeRemaining() > 6 || deadline.didTimeout)) {
        const fight = queue.shift();
        if (fight) {
          ensureBitmap(fight);
        }
      }
      if (queue.length > 0) {
        idleHandleRef.current = requestIdleCallbackShim(processQueue, { timeout: 32 });
      }
    };

    idleHandleRef.current = requestIdleCallbackShim(processQueue, { timeout: 32 });

    return () => {
      if (idleHandleRef.current) {
        cancelIdleCallbackShim(idleHandleRef.current);
        idleHandleRef.current = null;
      }
    };
  }, [ensureBitmap, preparedFights]);

  useEffect(() => {
    scheduleDraw();
  }, [drawPoints, scheduleDraw]);

  useEffect(() => {
    const overlay = overlayRef.current;
    if (!overlay) {
      return undefined;
    }

    const handleZoom = (event: D3ZoomEvent<HTMLDivElement, unknown>) => {
      transformRef.current = event.transform;
      scheduleDraw();
    };

    const zoomBehavior = zoom<HTMLDivElement, unknown>()
      .scaleExtent(ZOOM_SCALE_EXTENT)
      .translateExtent([
        [0, 0],
        [dimensions.width, dimensions.height],
      ])
      .on('zoom', handleZoom);

    const selection = select(overlay);
    selection.call(zoomBehavior as never);

    return () => {
      selection.on('.zoom', null);
    };
  }, [dimensions.height, dimensions.width, scheduleDraw]);

  useEffect(() => {
    if (!trendEnabled || preparedFights.length === 0) {
      setTrendLine([]);
      return;
    }

    if (typeof window === 'undefined') {
      return;
    }

    if (!trendWorkerRef.current) {
      trendWorkerRef.current = new Worker(new URL('../../workers/trendWorker.ts', import.meta.url));
    }

    const worker = trendWorkerRef.current;
    worker.onmessage = (event: MessageEvent<{ type: string; points: { x: number; y: number }[] }>) => {
      if (event.data.type === 'result') {
        setTrendLine(event.data.points);
        scheduleDraw();
      }
    };

    worker.postMessage({
      type: 'compute',
      points: preparedFights.map((item) => ({ x: item.dateValue, y: item.finishSeconds })),
    });

    return () => {
      worker.onmessage = null;
    };
  }, [preparedFights, scheduleDraw, trendEnabled]);

  useEffect(() => () => {
    trendWorkerRef.current?.terminate();
    trendWorkerRef.current = null;
  }, []);

  useEffect(() => {
    const overlay = overlayRef.current;
    if (!overlay) {
      return undefined;
    }

    const getPointerContext = (event: PointerEvent | MouseEvent | TouchEvent) => {
      const canvasRect = overlay.getBoundingClientRect();
      const [x, y] = pointerEvent(event, overlay);
      const transform = transformRef.current;
      const baseX = transform.invertX(x);
      const baseY = transform.invertY(y);
      return { baseX, baseY, canvasX: x, canvasY: y, rect: canvasRect };
    };

    const handlePointerMove = (event: PointerEvent) => {
      if (!quadtreeRef.current) {
        return;
      }
      const { baseX, baseY, canvasX, canvasY, rect } = getPointerContext(event);
      const searchRadius = (DEFAULT_MARKER_SIZE * 0.75) / transformRef.current.k;
      const nearest = quadtreeRef.current.find(baseX, baseY, searchRadius);
      if (nearest) {
        hoverIdRef.current = nearest.fight.id;
        setTooltip({
          fight: nearest.fight,
          position: {
            x: canvasX + rect.left,
            y: canvasY + rect.top,
          },
        });
      } else {
        hoverIdRef.current = null;
        setTooltip(null);
      }
      scheduleDraw();
    };

    const handlePointerLeave = () => {
      hoverIdRef.current = null;
      setTooltip(null);
      scheduleDraw();
    };

    const handleClick = (event: PointerEvent) => {
      if (!quadtreeRef.current) {
        return;
      }
      const { baseX, baseY } = getPointerContext(event);
      const searchRadius = (DEFAULT_MARKER_SIZE * 0.85) / transformRef.current.k;
      const nearest = quadtreeRef.current.find(baseX, baseY, searchRadius);
      if (nearest) {
        selectedIdRef.current = nearest.fight.id;
        scheduleDraw();
        onSelectFight?.(nearest.fight.id);
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
  }, [onSelectFight, scheduleDraw]);

  useEffect(() => {
    scheduleDraw();
  }, [densityEnabled, scheduleDraw, trendEnabled]);

  const formatTooltip = (fight: Fight) => {
    const finishMinutes = Math.floor(fight.finish_seconds / 60);
    const finishSeconds = fight.finish_seconds % 60;
    const finishLabel = `${finishMinutes}:${finishSeconds.toString().padStart(2, '0')}`;
    return [
      fight.opponentName ?? `Opponent ${fight.opponentId}`,
      fight.eventName ?? 'Unknown Event',
      `${fight.method} • ${fight.result}`,
      fight.round ? `Round ${fight.round} • ${fight.roundClock ?? finishLabel}` : `Duration ${finishLabel}`,
    ];
  };

  const tooltipLines = tooltip ? formatTooltip(tooltip.fight) : null;

  return (
    <div ref={containerRef} className="relative w-full h-full">
      <div className="absolute top-2 right-2 z-30 flex gap-2">
        <Button
          size="sm"
          variant={densityEnabled ? 'default' : 'secondary'}
          onClick={() => setDensityEnabled((state) => !state)}
        >
          {densityEnabled ? 'Hide Density' : 'Show Density'}
        </Button>
        <Button
          size="sm"
          variant={trendEnabled ? 'default' : 'secondary'}
          onClick={() => setTrendEnabled((state) => !state)}
        >
          {trendEnabled ? 'Hide Trend' : 'Show Trend'}
        </Button>
      </div>
      <canvas ref={heatmapCanvasRef} className="absolute inset-0 z-0" />
      <canvas ref={pointsCanvasRef} className="absolute inset-0 z-10" />
      <div ref={overlayRef} className="absolute inset-0 z-20 cursor-crosshair" />
      {tooltip && tooltipLines ? (
        <div
          className={clsx(
            'pointer-events-none absolute z-40 rounded-md border border-slate-200 bg-white px-3 py-2 text-xs shadow-lg transition-opacity',
          )}
          style={{
            top: tooltip.position.y + 12,
            left: tooltip.position.x + 12,
          }}
        >
          <div className="font-semibold text-slate-900">{tooltipLines[0]}</div>
          <div className="text-slate-500">{tooltipLines[1]}</div>
          <div className="mt-1 text-slate-600">{tooltipLines[2]}</div>
          <div className="text-slate-600">{tooltipLines[3]}</div>
          {tooltip.fight.eventUrl ? (
            <a
              href={tooltip.fight.eventUrl}
              target="_blank"
              rel="noreferrer"
              className="mt-1 inline-block text-blue-500 hover:underline"
            >
              View on UFC Stats
            </a>
          ) : null}
        </div>
      ) : null}
    </div>
  );
};

export default FightScatter;
