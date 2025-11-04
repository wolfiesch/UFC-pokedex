"use client";

import type { FightGraphQueryParams } from "@/lib/types";

type FightWebFiltersProps = {
  initialFilters?: FightGraphQueryParams;
};

export function FightWebFilters({ initialFilters }: FightWebFiltersProps) {
  const divisionLabel =
    initialFilters?.division && initialFilters.division.trim().length > 0
      ? initialFilters.division
      : "All divisions";
  const startYearLabel =
    typeof initialFilters?.startYear === "number" ? String(initialFilters.startYear) : "Any";
  const endYearLabel =
    typeof initialFilters?.endYear === "number" ? String(initialFilters.endYear) : "Any";
  const limitLabel =
    typeof initialFilters?.limit === "number" ? String(initialFilters.limit) : "Default";
  const upcomingLabel =
    typeof initialFilters?.includeUpcoming === "boolean"
      ? initialFilters.includeUpcoming
        ? "Included"
        : "Excluded"
      : "Excluded";

  return (
    <aside className="space-y-4 rounded-3xl border border-border/80 bg-card/60 p-6">
      <div>
        <h2 className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">
          Filters
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Interactive controls for narrowing the fight network will ship alongside the graph
          visualisation. For now, the default dataset is shown below.
        </p>
      </div>
      <dl className="space-y-2 text-sm text-foreground/80">
        <div className="flex items-center justify-between">
          <dt className="text-muted-foreground">Division</dt>
          <dd>{divisionLabel}</dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-muted-foreground">Start Year</dt>
          <dd>{startYearLabel}</dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-muted-foreground">End Year</dt>
          <dd>{endYearLabel}</dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-muted-foreground">Node Limit</dt>
          <dd>{limitLabel}</dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-muted-foreground">Upcoming Bouts</dt>
          <dd>{upcomingLabel}</dd>
        </div>
      </dl>
    </aside>
  );
}
