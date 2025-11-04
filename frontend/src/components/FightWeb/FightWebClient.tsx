"use client";

import { useMemo } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { FightGraphQueryParams, FightGraphResponse } from "@/lib/types";

import { FightGraphCanvas } from "./FightGraphCanvas";
import { FightWebFilters } from "./FightWebFilters";

type FightWebClientProps = {
  initialData: FightGraphResponse | null;
  initialFilters?: FightGraphQueryParams;
  initialError?: string | null;
};

function formatNumber(value: number): string {
  return value.toLocaleString("en-US");
}

function parseFilterNumber(value: unknown): number | null {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function FightWebClient({
  initialData,
  initialFilters,
  initialError,
}: FightWebClientProps) {
  const nodeCount = initialData?.nodes.length ?? 0;
  const linkCount = initialData?.links.length ?? 0;

  const metadata: Record<string, unknown> = initialData?.metadata ?? {};
  const filtersValueRaw = metadata["filters"];
  const filters =
    filtersValueRaw && typeof filtersValueRaw === "object" && !Array.isArray(filtersValueRaw)
      ? (filtersValueRaw as Record<string, unknown>)
      : null;

  const activeDivision =
    (typeof filters?.division === "string" && filters.division.length > 0
      ? filters.division
      : initialFilters?.division) || "All divisions";

  const activeStartYear =
    parseFilterNumber(filters?.start_year) ?? initialFilters?.startYear ?? null;
  const activeEndYear = parseFilterNumber(filters?.end_year) ?? initialFilters?.endYear ?? null;
  const activeLimit =
    parseFilterNumber(filters?.limit) ?? initialFilters?.limit ?? initialData?.nodes.length ?? 0;
  const includeUpcoming =
    typeof filters?.include_upcoming === "boolean"
      ? filters.include_upcoming
      : typeof initialFilters?.includeUpcoming === "boolean"
        ? initialFilters.includeUpcoming
        : false;

  const timeRangeLabel = useMemo(() => {
    if (activeStartYear && activeEndYear) {
      return `${activeStartYear} – ${activeEndYear}`;
    }
    if (activeStartYear) {
      return `${activeStartYear} onward`;
    }
    if (activeEndYear) {
      return `≤ ${activeEndYear}`;
    }
    return "All time";
  }, [activeEndYear, activeStartYear]);

  const currentFilters: FightGraphQueryParams = {
    division: activeDivision === "All divisions" ? null : activeDivision,
    startYear: activeStartYear ?? null,
    endYear: activeEndYear ?? null,
    limit: activeLimit,
    includeUpcoming,
  };

  return (
    <div className="space-y-8">
      {initialError ? (
        <div
          className="rounded-3xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive-foreground"
          role="alert"
        >
          {initialError}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle>Indexed Fighters</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-3xl font-semibold tracking-tight">
            {formatNumber(nodeCount)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Fight Connections</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-3xl font-semibold tracking-tight">
            {formatNumber(linkCount)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Division Scope</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-lg text-muted-foreground">{activeDivision}</CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Time Window</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-lg text-muted-foreground">
            {timeRangeLabel}
            <div className="mt-1 text-xs uppercase tracking-[0.3em] text-muted-foreground/80">
              Limit {formatNumber(activeLimit)}
              {" • "}
              {includeUpcoming ? "Upcoming included" : "Upcoming excluded"}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-[320px,1fr]">
        <FightWebFilters initialFilters={currentFilters} />
        <FightGraphCanvas data={initialData} />
      </div>
    </div>
  );
}
