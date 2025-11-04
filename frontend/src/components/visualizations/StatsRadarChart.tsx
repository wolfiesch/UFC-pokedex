"use client";

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface StatsRadarChartProps {
  striking: Record<string, string | number | null | undefined>;
  grappling: Record<string, string | number | null | undefined>;
}

function parsePercentage(value: string | number | null | undefined): number {
  if (value == null) return 0;
  const str = String(value).replace("%", "");
  const num = parseFloat(str);
  return isNaN(num) ? 0 : num;
}

function parseNumber(value: string | number | null | undefined): number {
  if (value == null) return 0;
  const num = parseFloat(String(value));
  return isNaN(num) ? 0 : num;
}

export function StatsRadarChart({ striking, grappling }: StatsRadarChartProps) {
  // Extract and normalize stats for radar chart
  const strikingAccuracy = parsePercentage(striking.sig_strikes_accuracy_pct);
  const strikingDefense = parsePercentage(striking.sig_strikes_defense_pct);
  const takedownAccuracy = parsePercentage(grappling.takedown_accuracy_pct);
  const takedownDefense = parsePercentage(grappling.takedown_defense_pct);

  // Normalize strikes per minute to 0-100 scale (assuming max ~10 per min)
  const strikesPerMin = parseNumber(striking.sig_strikes_landed_per_min);
  const normalizedStrikesPerMin = Math.min((strikesPerMin / 10) * 100, 100);

  // Normalize knockdowns to 0-100 scale (assuming max ~2 per fight)
  const knockdowns = parseNumber(striking.avg_knockdowns);
  const normalizedKnockdowns = Math.min((knockdowns / 2) * 100, 100);

  const data = [
    {
      metric: "Striking Accuracy",
      value: strikingAccuracy,
      fullMark: 100,
    },
    {
      metric: "Strike Defense",
      value: strikingDefense,
      fullMark: 100,
    },
    {
      metric: "Takedown Accuracy",
      value: takedownAccuracy,
      fullMark: 100,
    },
    {
      metric: "Takedown Defense",
      value: takedownDefense,
      fullMark: 100,
    },
    {
      metric: "Strikes/Min",
      value: normalizedStrikesPerMin,
      fullMark: 100,
      rawValue: strikesPerMin.toFixed(2),
    },
    {
      metric: "Knockdown Avg",
      value: normalizedKnockdowns,
      fullMark: 100,
      rawValue: knockdowns.toFixed(2),
    },
  ];

  // Check if we have any meaningful data
  const hasData = data.some((item) => item.value > 0);

  if (!hasData) {
    return (
      <Card className="bg-card/80">
        <CardHeader>
          <CardTitle className="text-xl">Performance Overview</CardTitle>
        </CardHeader>
        <CardContent className="flex h-[320px] items-center justify-center text-sm text-muted-foreground">
          No performance data available for this fighter.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/80">
      <CardHeader>
        <CardTitle className="text-xl">Performance Overview</CardTitle>
        <p className="text-sm text-muted-foreground">
          Key metrics visualized on a 0-100% scale. Hover for exact values.
        </p>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={320}>
          <RadarChart data={data}>
            <PolarGrid stroke="hsl(var(--border))" strokeOpacity={0.3} />
            <PolarAngleAxis
              dataKey="metric"
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
              stroke="hsl(var(--border))"
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10 }}
              stroke="hsl(var(--border))"
            />
            <Radar
              name="Fighter Stats"
              dataKey="value"
              stroke="hsl(var(--foreground))"
              fill="hsl(var(--foreground))"
              fillOpacity={0.15}
              strokeWidth={2}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--background))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "0.75rem",
                fontSize: "0.875rem",
              }}
              formatter={(value: number, name: string, props: any) => {
                const rawValue = props.payload.rawValue;
                if (rawValue !== undefined) {
                  return [rawValue, name];
                }
                return [`${value.toFixed(1)}%`, name];
              }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
