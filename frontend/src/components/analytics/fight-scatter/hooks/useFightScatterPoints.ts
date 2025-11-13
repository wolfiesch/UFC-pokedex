"use client";

import { useEffect, type RefObject } from "react";

import type { ScaleLinear, ScaleTime } from "d3-scale";

import { imageCache } from "@/lib/utils/imageCache";
import type {
  FightMethod,
  FightResult,
  TrendPoint,
} from "@/types/fight-scatter";

import { METHOD_ABBREV, VISUAL_CONFIG } from "../constants";
import { formatOpponentName } from "../utils";
import type { FightScatterDimensions, RenderedFight } from "../types";

/**
 * Options consumed by {@link useFightScatterPoints}.
 */
export interface UseFightScatterPointsOptions {
  /** Canvas ref that will receive the rendered fight markers. */
  canvasRef: RefObject<HTMLCanvasElement>;
  /** Render-time fight coordinates derived from scales + transforms. */
  renderedFights: RenderedFight[];
  /** Currently selected fight result filters. */
  filterResults: FightResult[];
  /** Currently selected fight method filters. */
  filterMethods: FightMethod[];
  /** Trend line samples computed in a background worker. */
  trendPoints: TrendPoint[];
  /** Whether the trend overlay is active. */
  showTrend: boolean;
  /** Chart dimensions for canvas resizing and clearing. */
  dimensions: FightScatterDimensions;
  /** X scale used for translating timestamps into screen space. */
  xScale: ScaleTime<number, number>;
  /** Y scale used for translating finish seconds into screen space. */
  yScale: ScaleLinear<number, number>;
  /** Current zoom/pan transform applied by d3-zoom. */
  transform: { scale: number; translateX: number; translateY: number };
}

/**
 * Imperatively renders fighter markers, labels, and overlays to the canvas.
 */
export function useFightScatterPoints({
  canvasRef,
  renderedFights,
  filterResults,
  filterMethods,
  trendPoints,
  showTrend,
  dimensions,
  xScale,
  yScale,
  transform,
}: UseFightScatterPointsOptions) {
  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");

    if (!canvas || !context) {
      return;
    }

    const dpr = window.devicePixelRatio || 1;
    canvas.width = dimensions.width * dpr;
    canvas.height = dimensions.height * dpr;
    context.scale(dpr, dpr);

    context.clearRect(0, 0, dimensions.width, dimensions.height);

    const hasFilters =
      filterResults.length > 0 || filterMethods.length > 0;

    for (const fight of renderedFights) {
      const { screenX: x, screenY: y, result, method } = fight;

      const resultMatch =
        filterResults.length === 0 || filterResults.includes(result);
      const methodMatch =
        filterMethods.length === 0 || filterMethods.includes(method);
      const matches = resultMatch && methodMatch;

      const opacity = hasFilters && !matches ? VISUAL_CONFIG.FILTER_OPACITY : 1;

      const placeholderKey = fight.opponent_id
        ? `placeholder:${fight.opponent_id}`
        : "";
      const bitmap =
        imageCache.get(placeholderKey) ||
        imageCache.get(fight.headshot_url || "");

      const radius = VISUAL_CONFIG.MARKER_SIZE / 2;

      context.save();
      context.globalAlpha = opacity;
      context.beginPath();
      context.arc(x, y, radius, 0, Math.PI * 2);
      context.clip();

      if (bitmap) {
        context.drawImage(
          bitmap,
          x - radius,
          y - radius,
          VISUAL_CONFIG.MARKER_SIZE,
          VISUAL_CONFIG.MARKER_SIZE
        );
      } else {
        context.fillStyle = "#95a5a6";
        context.fill();
      }

      context.restore();

      context.save();
      context.globalAlpha = opacity;
      context.strokeStyle =
        result === "W"
          ? VISUAL_CONFIG.COLORS.WIN
          : result === "L"
            ? VISUAL_CONFIG.COLORS.LOSS
            : VISUAL_CONFIG.COLORS.DRAW;
      context.lineWidth = VISUAL_CONFIG.BORDER_WIDTH;
      context.beginPath();
      context.arc(x, y, radius, 0, Math.PI * 2);
      context.stroke();
      context.restore();

      if (method !== "OTHER") {
        const badgeSize = VISUAL_CONFIG.BADGE_SIZE;
        const badgeX = x + radius - badgeSize - 2;
        const badgeY = y - radius + 2;

        context.save();
        context.globalAlpha = opacity;
        context.fillStyle = "rgba(0, 0, 0, 0.7)";
        context.fillRect(badgeX, badgeY, badgeSize, badgeSize);

        context.fillStyle = "#fff";
        context.font = "8px sans-serif";
        context.textAlign = "center";
        context.textBaseline = "middle";
        context.fillText(
          METHOD_ABBREV[method],
          badgeX + badgeSize / 2,
          badgeY + badgeSize / 2
        );
        context.restore();
      }

      if (fight.opponent_name) {
        const label = formatOpponentName(fight.opponent_name);
        const labelY = y - radius - 8;

        context.save();
        context.globalAlpha = opacity;
        context.shadowColor = "rgba(0, 0, 0, 0.8)";
        context.shadowBlur = 3;
        context.fillStyle = "#fff";
        context.font = "11px sans-serif";
        context.textAlign = "center";
        context.textBaseline = "bottom";
        context.fillText(label, x, labelY);
        context.restore();
      }
    }

    if (showTrend && trendPoints.length > 1) {
      context.save();
      context.strokeStyle = VISUAL_CONFIG.COLORS.TREND;
      context.lineWidth = 2;
      context.beginPath();
      trendPoints.forEach((point, index) => {
        const x =
          (xScale(new Date(point.x)) || 0) * transform.scale + transform.translateX;
        const y =
          (yScale(point.y) || 0) * transform.scale + transform.translateY;
        if (index === 0) {
          context.moveTo(x, y);
        } else {
          context.lineTo(x, y);
        }
      });
      context.stroke();
      context.restore();
    }
  }, [
    canvasRef,
    renderedFights,
    filterResults,
    filterMethods,
    trendPoints,
    showTrend,
    dimensions,
    xScale,
    yScale,
    transform,
  ]);
}
