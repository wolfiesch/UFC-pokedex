"use client";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { FightHistoryEntry } from "@/lib/types";

interface RecordBreakdownChartProps {
  record?: string | null;
  fightHistory: FightHistoryEntry[];
}

function parseRecord(record?: string | null): {
  wins: number;
  losses: number;
  draws: number;
} {
  if (!record) return { wins: 0, losses: 0, draws: 0 };

  // Record format: "11-5-0" (wins-losses-draws)
  const parts = record.split("-").map((n) => parseInt(n, 10));

  return {
    wins: parts[0] || 0,
    losses: parts[1] || 0,
    draws: parts[2] || 0,
  };
}

function getMethodBreakdown(fightHistory: FightHistoryEntry[]): {
  koTko: number;
  submission: number;
  decision: number;
  other: number;
} {
  const breakdown = {
    koTko: 0,
    submission: 0,
    decision: 0,
    other: 0,
  };

  // Only count wins for method breakdown
  const wins = fightHistory.filter((fight) =>
    fight.result.toLowerCase().includes("win"),
  );

  wins.forEach((fight) => {
    const method = fight.method.toUpperCase();
    if (method.includes("KO") || method.includes("TKO")) {
      breakdown.koTko++;
    } else if (method.includes("SUB")) {
      breakdown.submission++;
    } else if (method.includes("DEC") || method.includes("DECISION")) {
      breakdown.decision++;
    } else {
      breakdown.other++;
    }
  });

  return breakdown;
}

// Monochrome color palette with slight hue variations
const RESULT_COLORS = {
  win: "hsl(120, 15%, 45%)", // Greenish-gray
  loss: "hsl(0, 15%, 45%)", // Reddish-gray
  draw: "hsl(0, 0%, 50%)", // Pure gray
};

const METHOD_COLORS = {
  koTko: "hsl(0, 20%, 40%)", // Reddish
  submission: "hsl(270, 20%, 45%)", // Purple-ish
  decision: "hsl(210, 20%, 45%)", // Blue-ish
  other: "hsl(0, 0%, 50%)", // Gray
};

export function RecordBreakdownChart({
  record,
  fightHistory,
}: RecordBreakdownChartProps) {
  const { wins, losses, draws } = parseRecord(record);
  const methodBreakdown = getMethodBreakdown(fightHistory);

  const recordData = [
    { name: "Wins", value: wins, color: RESULT_COLORS.win },
    { name: "Losses", value: losses, color: RESULT_COLORS.loss },
    ...(draws > 0
      ? [{ name: "Draws", value: draws, color: RESULT_COLORS.draw }]
      : []),
  ];

  const methodData = [
    {
      name: "KO/TKO",
      value: methodBreakdown.koTko,
      color: METHOD_COLORS.koTko,
    },
    {
      name: "Submission",
      value: methodBreakdown.submission,
      color: METHOD_COLORS.submission,
    },
    {
      name: "Decision",
      value: methodBreakdown.decision,
      color: METHOD_COLORS.decision,
    },
    ...(methodBreakdown.other > 0
      ? [
          {
            name: "Other",
            value: methodBreakdown.other,
            color: METHOD_COLORS.other,
          },
        ]
      : []),
  ].filter((item) => item.value > 0);

  const hasMethodData =
    methodData.length > 0 && methodData.some((d) => d.value > 0);
  const hasRecordedWins = wins > 0;
  const hasWinHistory = fightHistory.some((fight) =>
    fight.result.toLowerCase().includes("win"),
  );

  const customLabel = ({
    cx,
    cy,
    midAngle,
    innerRadius,
    outerRadius,
    percent,
  }: any) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    if (percent < 0.05) return null; // Don't show labels for tiny slices

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? "start" : "end"}
        dominantBaseline="central"
        fontSize={12}
        fontWeight={600}
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <Card className="bg-card/80">
      <CardHeader>
        <CardTitle className="text-xl">Fight Record Breakdown</CardTitle>
        <p className="text-sm text-muted-foreground">
          Overall record and win methods distribution
        </p>
      </CardHeader>
      <CardContent>
        <div className="grid gap-8 md:grid-cols-2">
          {/* Record Distribution */}
          <div className="flex flex-col items-center">
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground">
              Win/Loss Record
            </h3>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={recordData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={2}
                  dataKey="value"
                  label={customLabel}
                  labelLine={false}
                >
                  {recordData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--background))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "0.75rem",
                    fontSize: "0.875rem",
                  }}
                />
                <Legend
                  verticalAlign="bottom"
                  height={36}
                  iconType="circle"
                  formatter={(value, entry: any) => (
                    <span className="text-sm text-foreground">
                      {value}: {entry.payload.value}
                    </span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Win Method Breakdown */}
          <div className="flex flex-col items-center">
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground">
              Win Methods
            </h3>
            {hasMethodData ? (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={methodData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                    label={customLabel}
                    labelLine={false}
                  >
                    {methodData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--background))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "0.75rem",
                      fontSize: "0.875rem",
                    }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    height={36}
                    iconType="circle"
                    formatter={(value, entry: any) => (
                      <span className="text-sm text-foreground">
                        {value}: {entry.payload.value}
                      </span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-[200px] items-center justify-center px-4 text-center text-sm text-muted-foreground">
                {hasRecordedWins && !hasWinHistory
                  ? "Win methods unavailable - detailed fight history not recorded"
                  : "No wins to analyze"}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
