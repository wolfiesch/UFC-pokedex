"use client";

import { memo } from "react";

import { formatMetricLabel } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type StatsDisplayProps = {
  title: string;
  stats: Record<string, string | number | null | undefined>;
};

function StatsDisplayComponent({ title, stats }: StatsDisplayProps) {
  return (
    <Card className="bg-card/80">
      <CardHeader className="space-y-1">
        <CardTitle className="text-xl">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-3 text-sm text-foreground/80 sm:grid-cols-3">
          {Object.entries(stats).map(([key, value]) => (
            <div key={key}>
              <dt className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                {formatMetricLabel(key)}
              </dt>
              <dd>{value ?? "—"}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

StatsDisplayComponent.displayName = "StatsDisplay";

export default memo(StatsDisplayComponent);
