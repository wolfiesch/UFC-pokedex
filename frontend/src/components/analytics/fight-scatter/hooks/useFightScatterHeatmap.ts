"use client";

import { useEffect, type RefObject } from "react";

import type { HexbinBucket } from "@/types/fight-scatter";

import type { FightScatterDimensions } from "../types";

/**
 * Draws the optional density heatmap layer whenever its inputs change.
 */
export interface UseFightScatterHeatmapOptions {
  /** Canvas element dedicated to the heatmap overlay. */
  canvasRef: RefObject<HTMLCanvasElement>;
  /** Toggle indicating whether the heatmap should be rendered. */
  showDensity: boolean;
  /** Pre-computed hexbins describing density buckets. */
  hexbins?: HexbinBucket[];
  /** Current chart dimensions in CSS pixels. */
  dimensions: FightScatterDimensions;
}

export function useFightScatterHeatmap({
  canvasRef,
  showDensity,
  hexbins,
  dimensions,
}: UseFightScatterHeatmapOptions) {
  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");

    if (!canvas || !context) {
      return;
    }

    if (!showDensity || !hexbins || hexbins.length === 0) {
      context.clearRect(0, 0, canvas.width, canvas.height);
      return;
    }

    const dpr = window.devicePixelRatio || 1;
    canvas.width = dimensions.width * dpr;
    canvas.height = dimensions.height * dpr;
    context.scale(dpr, dpr);

    context.clearRect(0, 0, dimensions.width, dimensions.height);

    const maxCount = Math.max(...hexbins.map((bucket) => bucket.count));
    const bucketSize = 50;

    for (const bucket of hexbins) {
      const alpha = Math.sqrt(bucket.count / maxCount);
      context.fillStyle = `rgba(231, 76, 60, ${alpha * 0.4})`;
      const x = bucket.i * bucketSize;
      const y = bucket.j * bucketSize;
      context.fillRect(x, y, bucketSize, bucketSize);
    }
  }, [canvasRef, showDensity, hexbins, dimensions]);
}
