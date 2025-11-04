"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface PerformanceBarChartsProps {
  striking: Record<string, string | number | null | undefined>;
  grappling: Record<string, string | number | null | undefined>;
}

function parsePercentage(value: string | number | null | undefined): number {
  if (value == null) return 0;
  const str = String(value).replace("%", "");
  const num = parseFloat(str);
  return isNaN(num) ? 0 : num;
}

function getBarColor(value: number): string {
  if (value >= 60) return "hsl(120, 25%, 45%)";
  if (value >= 40) return "hsl(45, 25%, 45%)";
  return "hsl(0, 25%, 45%)";
}

export function PerformanceBarCharts(props: PerformanceBarChartsProps) {
  const { striking, grappling } = props;

  const data = [
    {
      name: "Striking Accuracy",
      value: parsePercentage(striking.sig_strikes_accuracy_pct),
    },
    {
      name: "Strike Defense",
      value: parsePercentage(striking.sig_strikes_defense_pct),
    },
    {
      name: "Takedown Accuracy",
      value: parsePercentage(grappling.takedown_accuracy_pct),
    },
    {
      name: "Takedown Defense",
      value: parsePercentage(grappling.takedown_defense_pct),
    },
  ];

  const hasData = data.some((item) => item.value > 0);
  if (!hasData) return null;

  return (
    <Card className="bg-card/80">
      <CardHeader>
        <CardTitle className="text-xl">Accuracy &amp; Defense</CardTitle>
        <p className="text-sm text-muted-foreground">
          Key percentage metrics for striking and grappling performance
        </p>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 120, bottom: 5 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--border))"
              strokeOpacity={0.2}
              horizontal={true}
              vertical={false}
            />
            <XAxis
              type="number"
              domain={[0, 100]}
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
              stroke="hsl(var(--border))"
              tickFormatter={(value) => `${value}%`}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fill: "hsl(var(--foreground))", fontSize: 13 }}
              stroke="hsl(var(--border))"
              width={110}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--background))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "0.75rem",
                fontSize: "0.875rem",
              }}
              formatter={(value: number) => [`${value.toFixed(1)}%`, "Value"]}
              cursor={{ fill: "hsl(var(--muted))", opacity: 0.1 }}
            />
            <Bar dataKey="value" radius={[0, 8, 8, 0]}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(entry.value)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        <div className="mt-4 flex flex-wrap justify-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-sm"
              style={{ backgroundColor: "hsl(120, 25%, 45%)" }}
            />
            <span>Good (≥60%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-sm"
              style={{ backgroundColor: "hsl(45, 25%, 45%)" }}
            />
            <span>Average (40-59%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-sm"
              style={{ backgroundColor: "hsl(0, 25%, 45%)" }}
            />
            <span>Below Avg (&lt;40%)</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
