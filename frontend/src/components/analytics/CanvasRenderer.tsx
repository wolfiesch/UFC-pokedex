import { useEffect } from "react";
import type { ScaleLinear, ScaleTime } from "d3-scale";

import type {
  FightMethod,
  FightResult,
  HexbinBucket,
  TrendPoint,
  Transform,
} from "@/types/fight-scatter";
import { imageCache } from "@/lib/utils/imageCache";

import { FIGHT_SCATTER_VISUALS, METHOD_ABBREVIATIONS } from "./fightScatterConfig";
import type { RenderedFight, ScatterDimensions } from "./hooks/useFightScatterState";

export interface CanvasRendererProps {
  dimensions: ScatterDimensions;
  hexbins?: HexbinBucket[];
  heatmapCanvas: HTMLCanvasElement | null;
  pointsCanvas: HTMLCanvasElement | null;
  renderedFights: RenderedFight[];
  filterResults: FightResult[];
  filterMethods: FightMethod[];
  showDensity: boolean;
  showTrend: boolean;
  trendPoints: TrendPoint[];
  xScale: ScaleTime<number, number>;
  yScale: ScaleLinear<number, number>;
  transform: Transform;
}

/**
 * Imperatively paints both the heatmap and scatter point layers using the
 * provided refs. Keeping the drawing logic isolated makes the parent component
 * a thin orchestrator.
 */
export function CanvasRenderer({
  dimensions,
  hexbins,
  heatmapCanvas,
  pointsCanvas,
  renderedFights,
  filterResults,
  filterMethods,
  showDensity,
  showTrend,
  trendPoints,
  xScale,
  yScale,
  transform,
}: CanvasRendererProps): null {
  useEffect(() => {
    if (!showDensity || !hexbins || hexbins.length === 0) {
      const canvas = heatmapCanvas;
      if (canvas) {
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
      }
      return;
    }

    const canvas = heatmapCanvas;
    if (!canvas) {
      return;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }

    const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
    canvas.width = dimensions.width * dpr;
    canvas.height = dimensions.height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, dimensions.width, dimensions.height);

    const maxCount = Math.max(...hexbins.map((bin) => bin.count));
    const bucketSize = 50;

    for (const bin of hexbins) {
      const alpha = Math.sqrt(bin.count / maxCount);
      ctx.fillStyle = `rgba(231, 76, 60, ${alpha * 0.4})`;
      const x = bin.i * bucketSize;
      const y = bin.j * bucketSize;
      ctx.fillRect(x, y, bucketSize, bucketSize);
    }
  }, [dimensions.height, dimensions.width, heatmapCanvas, hexbins, showDensity]);

  useEffect(() => {
    const canvas = pointsCanvas;
    if (!canvas) {
      return;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }

    const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
    canvas.width = dimensions.width * dpr;
    canvas.height = dimensions.height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, dimensions.width, dimensions.height);

    const hasFilters = filterResults.length > 0 || filterMethods.length > 0;

    for (const fight of renderedFights) {
      const { screenX: x, screenY: y, result, method } = fight;
      const resultMatch = filterResults.length === 0 || filterResults.includes(result);
      const methodMatch = filterMethods.length === 0 || filterMethods.includes(method);
      const matches = resultMatch && methodMatch;
      const opacity = hasFilters && !matches ? FIGHT_SCATTER_VISUALS.FILTER_OPACITY : 1;

      const placeholderKey = fight.opponent_id ? `placeholder:${fight.opponent_id}` : "";
      const bitmap =
        imageCache.get(placeholderKey) || imageCache.get(fight.headshot_url || "");

      const radius = FIGHT_SCATTER_VISUALS.MARKER_SIZE / 2;

      ctx.save();
      ctx.globalAlpha = opacity;

      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.clip();

      if (bitmap) {
        ctx.drawImage(
          bitmap,
          x - radius,
          y - radius,
          FIGHT_SCATTER_VISUALS.MARKER_SIZE,
          FIGHT_SCATTER_VISUALS.MARKER_SIZE
        );
      } else {
        ctx.fillStyle = "#95a5a6";
        ctx.fill();
      }

      ctx.restore();

      ctx.save();
      ctx.globalAlpha = opacity;
      ctx.strokeStyle =
        result === "W"
          ? FIGHT_SCATTER_VISUALS.COLORS.WIN
          : result === "L"
            ? FIGHT_SCATTER_VISUALS.COLORS.LOSS
            : FIGHT_SCATTER_VISUALS.COLORS.DRAW;
      ctx.lineWidth = FIGHT_SCATTER_VISUALS.BORDER_WIDTH;
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();

      if (method !== "OTHER") {
        const badgeSize = FIGHT_SCATTER_VISUALS.BADGE_SIZE;
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
        ctx.fillText(METHOD_ABBREVIATIONS[method], badgeX + badgeSize / 2, badgeY + badgeSize / 2);
        ctx.restore();
      }

      if (fight.opponent_name) {
        const label = formatOpponentName(fight.opponent_name);
        const labelY = y - radius - 8;

        ctx.save();
        ctx.globalAlpha = opacity;
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

    if (showTrend && trendPoints.length > 1) {
      ctx.save();
      ctx.strokeStyle = FIGHT_SCATTER_VISUALS.COLORS.TREND;
      ctx.lineWidth = 2;
      ctx.beginPath();

      trendPoints.forEach((point, index) => {
        const x = (xScale(new Date(point.x)) || 0) * transform.scale + transform.translateX;
        const y = (yScale(point.y) || 0) * transform.scale + transform.translateY;

        if (index === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });

      ctx.stroke();
      ctx.restore();
    }
  }, [
    dimensions.height,
    dimensions.width,
    filterMethods,
    filterResults,
    pointsCanvas,
    renderedFights,
    showTrend,
    trendPoints,
    transform.scale,
    transform.translateX,
    transform.translateY,
    xScale,
    yScale,
  ]);

  return null;
}

function formatOpponentName(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 0) return "";
  if (parts.length === 1) return parts[0];
  const firstName = parts[0];
  const lastName = parts.slice(1).join(" ");
  return `${firstName.charAt(0)}. ${lastName}`;
}
