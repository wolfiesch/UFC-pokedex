"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type RankingDataPoint = {
  ranking_id: string;
  division: string;
  rank: number | null;
  previous_rank: number | null;
  rank_movement: number;
  is_interim: boolean;
  rank_date: string;
  source: string;
};

type RankingHistoryChartProps = {
  fighterName: string;
  history: RankingDataPoint[];
  division?: string;
};

export default function RankingHistoryChart({
  fighterName,
  history,
  division,
}: RankingHistoryChartProps) {
  // Transform data for Recharts (reverse to show oldest first, left to right)
  const chartData = useMemo(() => {
    return [...history].reverse().map((entry) => ({
      date: new Date(entry.rank_date).toLocaleDateString("en-US", {
        month: "short",
        year: "numeric",
      }),
      rank: entry.rank ?? null,
      division: entry.division,
      isChamp: entry.rank === 0,
      isInterim: entry.is_interim,
    }));
  }, [history]);

  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Ranking History</CardTitle>
          <CardDescription>
            {division ? `${division} Division` : "All Divisions"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No ranking history available for this fighter.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Custom tooltip to show rank details
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="rounded-lg border bg-background p-3 shadow-md">
          <p className="font-semibold">{data.date}</p>
          <p className="text-sm">Division: {data.division}</p>
          <p className="text-sm font-semibold">
            Rank:{" "}
            {data.isChamp
              ? data.isInterim
                ? "Champion (I)"
                : "Champion"
              : (data.rank ?? "NR")}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Ranking History</CardTitle>
        <CardDescription>
          {division ? `${division} Division` : "All Divisions"} •{" "}
          {chartData.length} snapshots
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              className="text-muted-foreground"
            />
            <YAxis
              reversed
              domain={[0, 15]}
              ticks={[0, 1, 5, 10, 15]}
              tickFormatter={(value) => (value === 0 ? "C" : value.toString())}
              tick={{ fontSize: 12 }}
              label={{ value: "Rank", angle: -90, position: "insideLeft" }}
              className="text-muted-foreground"
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Line
              type="monotone"
              dataKey="rank"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={{ fill: "hsl(var(--primary))", r: 4 }}
              activeDot={{ r: 6 }}
              name="Rank"
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
        <p className="mt-4 text-xs text-muted-foreground">
          Lower rank number = higher position. Champion = 0. NR = Not Ranked.
        </p>
      </CardContent>
    </Card>
  );
}
