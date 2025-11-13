"use client";

import type { PropsWithChildren, RefObject } from "react";

export interface FightScatterCanvasStackProps extends PropsWithChildren {
  /** Heatmap canvas ref layered underneath fighter markers. */
  heatmapCanvasRef: RefObject<HTMLCanvasElement>;
  /** Points canvas ref that renders fighters, badges, and labels. */
  pointsCanvasRef: RefObject<HTMLCanvasElement>;
  /** Desired height of the stacked canvases. */
  height: number;
}

/**
 * Hosts the layered canvases and any absolutely positioned overlays.
 */
export function FightScatterCanvasStack({
  heatmapCanvasRef,
  pointsCanvasRef,
  height,
  children,
}: FightScatterCanvasStackProps) {
  return (
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
      {children}
    </div>
  );
}
