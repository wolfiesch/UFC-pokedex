"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import type { FightWebInsights } from "./insight-utils";

type FightWebInsightsPanelProps = {
  insights: FightWebInsights;
  onSelectFighter?: (fighterId: string) => void;
};

/**
 * Show contextual network insights such as top hubs and high-volume rivalries.
 */
export function FightWebInsightsPanel({
  insights,
  onSelectFighter,
}: FightWebInsightsPanelProps) {
  return (
    <Card className="border border-border/80 bg-card/60">
      <CardHeader>
        <CardTitle className="text-sm font-semibold uppercase tracking-[0.3em] text-muted-foreground">
          Network insights
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6 text-sm text-muted-foreground">
        <section className="space-y-2">
          <h3 className="text-xs uppercase tracking-[0.3em] text-muted-foreground/70">
            Top fight hubs
          </h3>
          {insights.topFighters.length === 0 ? (
            <p>No fighters available for this filter set.</p>
          ) : (
            <ul className="space-y-1">
              {insights.topFighters.map((fighter) => (
                <li key={fighter.fighterId}>
                  <button
                    type="button"
                    onClick={() => onSelectFighter?.(fighter.fighterId)}
                    className="flex w-full items-center justify-between rounded-2xl border border-border/70 bg-background/60 px-3 py-2 text-left text-foreground transition hover:border-foreground hover:bg-background"
                  >
                    <span className="font-medium text-foreground/90">
                      {fighter.name}
                      <span className="ml-2 text-xs uppercase tracking-[0.3em] text-muted-foreground/70">
                        {fighter.division ?? "Unlisted"}
                      </span>
                    </span>
                    <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
                      {fighter.totalFights} fights
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="space-y-2">
          <h3 className="text-xs uppercase tracking-[0.3em] text-muted-foreground/70">
            High-volume rivalries
          </h3>
          {insights.busiestRivalries.length === 0 ? (
            <p>No rivalry data available for this view.</p>
          ) : (
            <ul className="space-y-1">
              {insights.busiestRivalries.map((rivalry) => (
                <li
                  key={`${rivalry.source}-${rivalry.target}`}
                  className="rounded-2xl border border-border/70 bg-background/40 px-3 py-2"
                >
                  <div className="flex items-center justify-between text-foreground">
                    <span className="font-medium text-foreground/90">
                      {rivalry.sourceName ?? rivalry.source}
                      <span className="mx-2 text-xs uppercase tracking-[0.3em] text-muted-foreground/60">
                        vs
                      </span>
                      {rivalry.targetName ?? rivalry.target}
                    </span>
                    <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
                      {rivalry.fights} fights
                    </span>
                  </div>
                  {rivalry.lastEventName ? (
                    <p className="mt-1 text-xs text-muted-foreground/80">
                      Last met at {rivalry.lastEventName}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </section>
      </CardContent>
    </Card>
  );
}
