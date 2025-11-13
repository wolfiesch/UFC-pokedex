"use client";

import dynamic from "next/dynamic";
import { Suspense, type ReactNode } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { TrendSeries } from "@/lib/types";
import type { TrendChartInnerProps } from "./TrendChartInner";

const Chart = dynamic<TrendChartInnerProps>(() => import("./TrendChartInner"), {
  ssr: false,
  loading: () => (
    <div
      className="py-10 text-center text-sm text-muted-foreground"
      role="status"
    >
      Preparing chart visualisation…
    </div>
  ),
});

export interface TrendChartProps {
  title: string;
  description?: string;
  series: TrendSeries[];
  isLoading?: boolean;
  error?: string | null;
}

export default function TrendChart({
  title,
  description,
  series,
  isLoading = false,
  error,
}: TrendChartProps) {
  let content: ReactNode;

  if (error) {
    content = (
      <div
        className="rounded-2xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive-foreground"
        role="alert"
      >
        {error}
      </div>
    );
  } else if (isLoading) {
    content = (
      <div
        className="py-10 text-center text-sm text-muted-foreground"
        role="status"
      >
        Loading trend data…
      </div>
    );
  } else if (series.length === 0) {
    content = (
      <div
        className="py-10 text-center text-sm text-muted-foreground"
        role="status"
      >
        No trend information is available for this metric yet.
      </div>
    );
  } else {
    content = (
      <Suspense
        fallback={
          <div
            className="py-10 text-center text-sm text-muted-foreground"
            role="status"
          >
            Preparing chart visualisation…
          </div>
        }
      >
        <Chart series={series} />
      </Suspense>
    );
  }

  return (
    <Card className="rounded-3xl border-border bg-card/80">
      <CardHeader className="space-y-2">
        <CardTitle className="text-xl">{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>{content}</CardContent>
    </Card>
  );
}
