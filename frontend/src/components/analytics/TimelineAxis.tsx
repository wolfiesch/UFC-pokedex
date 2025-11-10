import { useMemo } from "react";
import type { ScaleTime } from "d3-scale";

import { generateMonthlyTicks } from "@/lib/fight-scatter-utils";
import type { Transform } from "@/types/fight-scatter";

import type { ScatterDimensions, ScatterDomain } from "./hooks/useFightScatterState";

interface TimelineAxisProps {
  domain: ScatterDomain;
  dimensions: ScatterDimensions;
  xScale: ScaleTime<number, number>;
  transform: Transform;
}

/**
 * Declarative SVG timeline that renders hierarchical month and year ticks.
 */
export function TimelineAxis({ domain, dimensions, xScale, transform }: TimelineAxisProps) {
  const ticks = useMemo(() => {
    const startYear = new Date(domain.xMin).getFullYear();
    const endYear = new Date(domain.xMax).getFullYear();
    return generateMonthlyTicks(startYear, endYear).map((timestamp) => new Date(timestamp));
  }, [domain.xMax, domain.xMin]);

  return (
    <svg className="absolute left-0 top-0 pointer-events-none" style={{ width: "100%", height: "100%" }}>
      {ticks.map((date) => {
        const month = date.getMonth();
        const year = date.getFullYear();
        const baseX = xScale(date) || 0;
        const x = baseX * transform.scale + transform.translateX;

        if (x < 0 || x > dimensions.width) {
          return null;
        }

        const isYearStart = month === 0;
        const isQuarterly = month === 2 || month === 5 || month === 8;

        const tickHeight = isYearStart ? 12 : isQuarterly ? 8 : 5;
        const strokeWidth = isYearStart ? 2.5 : isQuarterly ? 1.8 : 1;
        const opacity = isYearStart ? 1 : isQuarterly ? 0.8 : 0.4;
        const yStart = dimensions.height - 30;

        return (
          <g key={`timeline-${year}-${month}`}>
            <line
              x1={x}
              y1={yStart}
              x2={x}
              y2={yStart + tickHeight}
              stroke="hsl(var(--border))"
              strokeWidth={strokeWidth}
              opacity={opacity}
            />
            {isYearStart ? (
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
            ) : null}
          </g>
        );
      })}
    </svg>
  );
}
