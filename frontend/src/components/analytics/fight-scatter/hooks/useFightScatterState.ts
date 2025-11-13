"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { scaleLinear, scaleTime, type ScaleLinear, type ScaleTime } from "d3-scale";
import { zoom as d3Zoom, type D3ZoomEvent } from "d3-zoom";
import { quadtree, type Quadtree } from "d3-quadtree";
import { select } from "d3-selection";

import { computeDomain } from "@/lib/fight-scatter-utils";
import { imageCache } from "@/lib/utils/imageCache";
import type {
  Transform,
  TooltipState,
  TrendPoint,
  TrendWorkerRequest,
  TrendWorkerResponse,
  ScatterFight,
} from "@/types/fight-scatter";

import { VISUAL_CONFIG } from "../constants";
import type { FightScatterDimensions, RenderedFight } from "../types";

/**
 * Parameters accepted by {@link useFightScatterState}.
 */
export interface UseFightScatterStateOptions {
  /** Fights to visualise. */
  fights: ScatterFight[];
  /** Optional override for the Y domain to keep charts aligned across fighters. */
  domainY?: [number, number];
  /** Requested chart height in CSS pixels. */
  height: number;
  /** Whether the trend worker should stay active. */
  showTrend: boolean;
}

/**
 * Aggregates FightScatter stateful concerns (dimensions, transforms, workers)
 * into a composable hook so the visual component can remain declarative.
 */
export function useFightScatterState({
  fights,
  domainY,
  height,
  showTrend,
}: UseFightScatterStateOptions) {
  const containerRef = useRef<HTMLDivElement>(null);
  const heatmapCanvasRef = useRef<HTMLCanvasElement>(null);
  const pointsCanvasRef = useRef<HTMLCanvasElement>(null);
  const overlayRef = useRef<SVGSVGElement>(null);
  const workerRef = useRef<Worker | null>(null);

  const [dimensions, setDimensions] = useState<FightScatterDimensions>({
    width: 800,
    height,
  });
  const [transform, setTransform] = useState<Transform>({
    scale: 1,
    translateX: 0,
    translateY: 0,
  });
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const [trendPoints, setTrendPoints] = useState<TrendPoint[]>([]);
  const [imagesLoaded, setImagesLoaded] = useState(false);

  // Keep local height in sync with props without stomping on width updates.
  useEffect(() => {
    setDimensions((prev) => ({ ...prev, height }));
  }, [height]);

  const domain = useMemo(() => {
    const computed = computeDomain(fights);
    return {
      ...computed,
      yMin: domainY ? domainY[0] : computed.yMin,
      yMax: domainY ? domainY[1] : computed.yMax,
    };
  }, [fights, domainY]);

  const xScale: ScaleTime<number, number> = useMemo(
    () =>
      scaleTime<number, number>()
        .domain([new Date(domain.xMin), new Date(domain.xMax)])
        .range([40, dimensions.width - 40]),
    [domain.xMin, domain.xMax, dimensions.width]
  );

  const yScale: ScaleLinear<number, number> = useMemo(
    () =>
      scaleLinear()
        .domain([domain.yMax, domain.yMin])
        .range([40, dimensions.height - 40]),
    [domain.yMin, domain.yMax, dimensions.height]
  );

  const renderedFights = useMemo<RenderedFight[]>(() => {
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

  const quadTree = useMemo<Quadtree<RenderedFight>>(() => {
    return quadtree<RenderedFight>()
      .x((d) => d.screenX)
      .y((d) => d.screenY)
      .addAll(renderedFights);
  }, [renderedFights]);

  useEffect(() => {
    let cancelled = false;
    const loadImages = async () => {
      setImagesLoaded(false);
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
      if (!cancelled) {
        setImagesLoaded(true);
      }
    };

    void loadImages();

    return () => {
      cancelled = true;
    };
  }, [fights]);

  useEffect(() => {
    if (typeof Worker === "undefined") {
      return;
    }

    const worker = new Worker(
      new URL("../../../../workers/trendWorker.ts", import.meta.url)
    );
    workerRef.current = worker;

    const handleMessage = (event: MessageEvent<TrendWorkerResponse>) => {
      if (event.data.type === "result" && event.data.points) {
        setTrendPoints(event.data.points);
      }
    };

    worker.addEventListener("message", handleMessage);

    return () => {
      worker.removeEventListener("message", handleMessage);
      worker.terminate();
      workerRef.current = null;
    };
  }, []);

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

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setDimensions((prev) => ({
          width: entry.contentRect.width,
          height: prev.height,
        }));
      }
    });

    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    const overlay = overlayRef.current;
    if (!overlay) {
      return;
    }

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

  return {
    containerRef,
    heatmapCanvasRef,
    pointsCanvasRef,
    overlayRef,
    dimensions,
    transform,
    tooltip,
    setTooltip,
    trendPoints,
    imagesLoaded,
    domain,
    xScale,
    yScale,
    renderedFights,
    quadTree,
  };
}
