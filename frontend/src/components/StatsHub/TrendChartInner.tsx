"use client";

import { memo, useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TrendSeries } from "@/lib/types";

/** Palette of high-contrast monochrome tones for multi-series charts. */
const SERIES_COLORS = ["#0a0a0a", "#2f2f2f", "#555555", "#7a7a7a", "#a0a0a0", "#cfcfcf"];

/**
 * Props definition for the inner chart component that directly utilises the
 * `recharts` primitives. This component is dynamically imported by
 * `TrendChart.tsx` to avoid server-side rendering pitfalls.
 */
export interface TrendChartInnerProps {
  /** Set of series to visualise; each entry should be chronologically sorted. */
  series: TrendSeries[];
}

interface ChartDatum {
  timestamp: string;
  label: string;
  [seriesKey: string]: string | number;
}

function formatTimestampLabel(timestamp: string): string {
  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) {
    return timestamp;
  }
  return parsed.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function getDisplayKey(index: number, label: string): string {
  if (label.trim().length > 0) {
    return label;
  }
  return `Series ${index + 1}`;
}

function buildChartData(series: TrendSeries[]): { data: ChartDatum[]; keys: string[] } {
  const dataMap = new Map<string, ChartDatum>();
  const keys: string[] = [];

  series.forEach((serie, seriesIndex) => {
    const key = getDisplayKey(seriesIndex, serie.label);
    keys.push(key);
    serie.points.forEach((point) => {
      const existing = dataMap.get(point.timestamp);
      if (existing) {
        existing[key] = point.value;
        return;
      }
      dataMap.set(point.timestamp, {
        timestamp: point.timestamp,
        label: formatTimestampLabel(point.timestamp),
        [key]: point.value,
      });
    });
  });

  const data = Array.from(dataMap.values()).sort((a, b) =>
    a.timestamp.localeCompare(b.timestamp)
  );

  return { data, keys };
}

/**
 * Pure rendering layer around the `LineChart` component. The heavy lifting such
 * as memoising the aggregated dataset and mapping series keys happens here,
 * allowing the wrapper component to remain minimal.
 */
function TrendChartInnerComponent({ series }: TrendChartInnerProps) {
  const { data, keys } = useMemo(() => buildChartData(series), [series]);

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 16, right: 24, bottom: 16, left: 0 }}>
        <CartesianGrid stroke="#e5e5e5" strokeDasharray="4 4" />
        <XAxis dataKey="label" stroke="#525252" tickLine={false} axisLine={false} />
        <YAxis stroke="#525252" tickLine={false} axisLine={false} allowDecimals />
        <Tooltip
          contentStyle={{
            backgroundColor: "#ffffff",
            borderColor: "#1f1f1f",
            color: "#111111",
          }}
          labelFormatter={(value) => `Date: ${value}`}
        />
        <Legend />
        {keys.map((key, index) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            stroke={SERIES_COLORS[index % SERIES_COLORS.length]}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export default memo(TrendChartInnerComponent);
