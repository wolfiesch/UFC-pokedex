"use client";

import {
  useCallback,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";

import type { FightScatterProps } from "@/types/fight-scatter";

import { FightTooltip } from "../FightTooltip";
import { VISUAL_CONFIG } from "./constants";
import { FightScatterCanvasStack } from "./components/FightScatterCanvasStack";
import { FightScatterLoadingIndicator } from "./components/FightScatterLoadingIndicator";
import { FightScatterTimelineAxis } from "./components/FightScatterTimelineAxis";
import { useFightScatterHeatmap } from "./hooks/useFightScatterHeatmap";
import { useFightScatterPoints } from "./hooks/useFightScatterPoints";
import { useFightScatterState } from "./hooks/useFightScatterState";

/**
 * High level orchestration component that stitches together hooks + layers.
 */
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
  const {
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
  } = useFightScatterState({ fights, domainY, height, showTrend });

  useFightScatterHeatmap({
    canvasRef: heatmapCanvasRef,
    showDensity,
    hexbins,
    dimensions,
  });

  useFightScatterPoints({
    canvasRef: pointsCanvasRef,
    renderedFights,
    filterResults,
    filterMethods,
    trendPoints,
    showTrend,
    dimensions,
    xScale,
    yScale,
    transform,
  });

  const handlePointerMove = useCallback(
    (event: ReactPointerEvent<SVGSVGElement>) => {
      const rect = overlayRef.current?.getBoundingClientRect();
      if (!rect) {
        return;
      }

      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
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
    [overlayRef, quadTree, setTooltip]
  );

  const handlePointerLeave = useCallback(() => {
    setTooltip(null);
  }, [setTooltip]);

  const handleClick = useCallback(
    (event: ReactMouseEvent<SVGSVGElement>) => {
      if (!onSelectFight) {
        return;
      }

      const rect = overlayRef.current?.getBoundingClientRect();
      if (!rect) {
        return;
      }

      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const nearest = quadTree.find(x, y, VISUAL_CONFIG.HIT_TEST_RADIUS);

      if (nearest) {
        onSelectFight(nearest.id);
      }
    },
    [overlayRef, quadTree, onSelectFight]
  );

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <FightScatterCanvasStack
        heatmapCanvasRef={heatmapCanvasRef}
        pointsCanvasRef={pointsCanvasRef}
        height={height}
      >
        <FightScatterTimelineAxis
          domain={domain}
          xScale={xScale}
          transform={transform}
          dimensions={dimensions}
        />
        <svg
          ref={overlayRef}
          className="absolute left-0 top-0 cursor-move"
          style={{ width: "100%", height: "100%" }}
          onPointerMove={handlePointerMove}
          onPointerLeave={handlePointerLeave}
          onClick={handleClick}
        />
      </FightScatterCanvasStack>

      {tooltip && <FightTooltip fight={tooltip.fight} x={tooltip.x} y={tooltip.y} />}

      <FightScatterLoadingIndicator visible={!imagesLoaded} />
    </div>
  );
}
