"use client";

import type { FavoriteCollectionStats } from "@/lib/types";
import { FighterLink } from "@/components/fighter/FighterLink";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export type StatsSummaryProps = {
  /** Title for contextual headings. */
  collectionName: string;
  /** Aggregated statistics computed by the backend. */
  stats: FavoriteCollectionStats;
};

/**
 * Present a concise overview of collection performance including win rate,
 * division coverage, and any upcoming fights that require attention.
 */
export function StatsSummary({ collectionName, stats }: StatsSummaryProps) {
  const winRatePercent = Math.round(stats.win_rate * 1000) / 10;
  const breakdownEntries = Object.entries(stats.result_breakdown ?? {});

  return (
    <section aria-labelledby="favorites-summary-heading" className="space-y-4">
      <header>
        <h2
          id="favorites-summary-heading"
          className="text-xl font-bold tracking-tight"
        >
          {collectionName} snapshot
        </h2>
        <p className="text-sm text-muted-foreground">
          Quick metrics summarising how this curated roster is performing.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="border-border/60 bg-card/80">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              Total fighters
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{stats.total_fighters}</p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/80">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              Win rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{winRatePercent.toFixed(1)}%</p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/80">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              Divisions represented
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{stats.divisions.length}</p>
            <p className="mt-2 text-xs text-muted-foreground">
              {stats.divisions.length
                ? stats.divisions.join(", ")
                : "No divisions recorded"}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/60 bg-card/80">
        <CardHeader>
          <CardTitle className="text-sm font-semibold text-muted-foreground">
            Result breakdown
          </CardTitle>
        </CardHeader>
        <CardContent>
          {breakdownEntries.length ? (
            <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-3">
              {breakdownEntries.map(([key, value]) => (
                <div key={key} className="rounded-lg bg-muted/40 p-3">
                  <dt className="text-xs uppercase tracking-wide text-muted-foreground">
                    {key}
                  </dt>
                  <dd className="text-lg font-semibold">{value}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="text-sm text-muted-foreground">
              No fight history has been recorded yet.
            </p>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/60 bg-card/80">
        <CardHeader>
          <CardTitle className="text-sm font-semibold text-muted-foreground">
            Upcoming fights
          </CardTitle>
        </CardHeader>
        <CardContent>
          {stats.upcoming_fights.length ? (
            <ul className="space-y-2 text-sm">
              {stats.upcoming_fights.map((fight) => (
                <li
                  key={`${fight.fighter_id}-${fight.event_name}`}
                  className="flex flex-col gap-1 rounded-lg border border-border/40 bg-background/40 p-3"
                >
                  <span className="font-semibold text-foreground">
                    <FighterLink
                      fighterId={fight.fighter_id}
                      name={fight.fighter_name ?? fight.fighter_id}
                      className="font-semibold"
                    />
                  </span>
                  <span className="flex flex-wrap items-center gap-1 text-muted-foreground">
                    <span>vs</span>
                    <FighterLink
                      fighterId={fight.opponent_id ?? null}
                      name={fight.opponent_name ?? "TBD"}
                      className="text-muted-foreground"
                    />
                    <span>— {fight.event_name}</span>
                  </span>
                  {fight.event_date ? (
                    <span className="text-xs text-muted-foreground/80">
                      {fight.event_date}
                    </span>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              No upcoming bouts scheduled.
            </p>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

export default StatsSummary;
