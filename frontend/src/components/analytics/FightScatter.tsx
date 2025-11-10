"use client";

import {
  useCallback,
  useMemo,
  useState,
} from "react";
import type {
  MouseEvent as ReactMouseEvent,
  PointerEvent as ReactPointerEvent,
} from "react";

import type {
  FightScatterProps,
  TooltipState,
  TrendPoint,
  Transform,
} from "@/types/fight-scatter";

import { CanvasRenderer } from "./CanvasRenderer";
import { FightTooltip } from "./FightTooltip";
import { TimelineAxis } from "./TimelineAxis";
import { TrendWorkerProvider } from "./TrendWorkerProvider";
import { FIGHT_SCATTER_VISUALS } from "./fightScatterConfig";
import {
  useFightScatterState,
  type RenderedFight,
} from "./hooks/useFightScatterState";
import { useOpponentImagePreload } from "./hooks/useOpponentImagePreload";
import { useResizeObserver } from "./hooks/useResizeObserver";
import { useZoomTransform } from "./hooks/useZoomTransform";

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
  const [containerNode, setContainerNode] = useState<HTMLDivElement | null>(null);
  const [heatmapCanvas, setHeatmapCanvas] = useState<HTMLCanvasElement | null>(null);
  const [pointsCanvas, setPointsCanvas] = useState<HTMLCanvasElement | null>(null);
  const [overlayNode, setOverlayNode] = useState<SVGSVGElement | null>(null);
  const [transform, setTransform] = useState<Transform>({
    scale: 1,
    translateX: 0,
    translateY: 0,
  });
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  const dimensions = useResizeObserver({ element: containerNode, height });

  const scatterState = useFightScatterState({
    fights,
    domainY,
    dimensions,
    transform,
  });

  const imagesLoaded = useOpponentImagePreload(fights);

  const handleTransform = useCallback(
    (next: typeof transform) => {
      setTransform(next);
    },
    []
  );

  useZoomTransform({
    overlay: overlayNode,
    extent: FIGHT_SCATTER_VISUALS.ZOOM_EXTENT,
    onTransform: handleTransform,
  });

  const trendInput = useMemo<TrendPoint[]>(
    () =>
      fights.map((fight) => ({
        x: new Date(fight.date).getTime(),
        y: fight.finish_seconds,
      })),
    [fights]
  );

  const handlePointerMove = useCallback(
    (event: ReactPointerEvent<SVGSVGElement>) => {
      if (!overlayNode) return;
      const rect = overlayNode.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;

      const nearest = scatterState.quadTree.find(
        x,
        y,
        FIGHT_SCATTER_VISUALS.HIT_TEST_RADIUS
      ) as RenderedFight | undefined;

      if (nearest) {
        setTooltip({ x: event.clientX, y: event.clientY, fight: nearest });
      } else {
        setTooltip(null);
      }
    },
    [overlayNode, scatterState.quadTree]
  );

  const handlePointerLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  const handleClick = useCallback(
    (event: ReactMouseEvent<SVGSVGElement>) => {
      if (!onSelectFight || !overlayNode) return;
      const rect = overlayNode.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const nearest = scatterState.quadTree.find(
        x,
        y,
        FIGHT_SCATTER_VISUALS.HIT_TEST_RADIUS
      ) as RenderedFight | undefined;

      if (nearest) {
        onSelectFight(nearest.id);
      }
    },
    [onSelectFight, overlayNode, scatterState.quadTree]
  );

  return (
    <TrendWorkerProvider enabled={showTrend} points={trendInput}>
      {({ trendPoints, isWorkerAvailable }) => {
        const resolvedTrendPoints = isWorkerAvailable
          ? trendPoints
          : showTrend
            ? trendInput
            : [];

        return (
        <div ref={setContainerNode} className={`relative ${className}`}>
          <div className="relative" style={{ width: "100%", height: `${height}px` }}>
            <canvas
              ref={setHeatmapCanvas}
              className="absolute left-0 top-0"
              style={{ width: "100%", height: "100%" }}
            />
            <canvas
              ref={setPointsCanvas}
              className="absolute left-0 top-0"
              style={{ width: "100%", height: "100%" }}
            />

            <TimelineAxis
              domain={scatterState.domain}
              dimensions={dimensions}
              xScale={scatterState.xScale}
              transform={transform}
            />

            <svg
              ref={setOverlayNode}
              className="absolute left-0 top-0 cursor-move"
              style={{ width: "100%", height: "100%" }}
              onPointerMove={handlePointerMove}
              onPointerLeave={handlePointerLeave}
              onClick={handleClick}
            />

            <CanvasRenderer
              dimensions={dimensions}
              hexbins={hexbins}
              heatmapCanvas={heatmapCanvas}
              pointsCanvas={pointsCanvas}
              renderedFights={scatterState.renderedFights}
              filterResults={filterResults}
              filterMethods={filterMethods}
              showDensity={showDensity}
              showTrend={showTrend}
              trendPoints={resolvedTrendPoints}
              xScale={scatterState.xScale}
              yScale={scatterState.yScale}
              transform={transform}
            />
          </div>

          {tooltip ? (
            <FightTooltip fight={tooltip.fight} x={tooltip.x} y={tooltip.y} />
          ) : null}

          {!imagesLoaded ? (
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-lg bg-gray-900/90 px-4 py-2 text-sm text-white">
              Loading images...
            </div>
          ) : null}
        </div>
        );
      }}
    </TrendWorkerProvider>
  );
}
