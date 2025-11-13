"use client";

import { useMemo } from "react";
import type { ScaleTime } from "d3-scale";

import { generateMonthlyTicks } from "@/lib/fight-scatter-utils";
import type { Transform } from "@/types/fight-scatter";

import type { FightScatterDimensions } from "../types";

export interface FightScatterTimelineAxisProps {
  /** Computed domain boundaries for the scatter plot. */
  domain: { xMin: number; xMax: number };
  /** Time scale translating fight dates to screen coordinates. */
  xScale: ScaleTime<number, number>;
  /** Current zoom/pan transform that should influence tick placement. */
  transform: Transform;
  /** Container dimensions so we can cull off-screen ticks. */
  dimensions: FightScatterDimensions;
}

/**
 * Renders the horizontal time axis with hierarchical month/year ticks.
 */
export function FightScatterTimelineAxis({
  domain,
  xScale,
  transform,
  dimensions,
}: FightScatterTimelineAxisProps) {
  const ticks = useMemo(() => {
    const start = new Date(domain.xMin);
    const end = new Date(domain.xMax);
    const rawTicks = generateMonthlyTicks(
      start.getFullYear(),
      end.getFullYear()
    );
    return rawTicks.filter((timestamp) =>
      timestamp >= domain.xMin - 32 * 24 * 60 * 60 * 1000 &&
      timestamp <= domain.xMax + 32 * 24 * 60 * 60 * 1000
    );
  }, [domain]);

  const yStart = dimensions.height - 30;

  return (
    <svg
      className="pointer-events-none absolute left-0 top-0"
      style={{ width: "100%", height: "100%" }}
    >
      {ticks.map((timestamp) => {
        const date = new Date(timestamp);
        const month = date.getMonth();
        const year = date.getFullYear();
        const x = (xScale(date) || 0) * transform.scale + transform.translateX;

        if (x < 0 || x > dimensions.width) {
          return null;
        }

        const isYearStart = month === 0;
        const isQuarterly = month === 2 || month === 5 || month === 8;

        const tickHeight = isYearStart ? 12 : isQuarterly ? 8 : 5;
        const strokeWidth = isYearStart ? 2.5 : isQuarterly ? 1.8 : 1;
        const opacity = isYearStart ? 1 : isQuarterly ? 0.8 : 0.4;

        return (
          <g key={`${year}-${month}-${timestamp}`}>
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
      })}
    </svg>
  );
}
