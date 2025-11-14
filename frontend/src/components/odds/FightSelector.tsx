"use client";

import { format } from "date-fns";

import type { FighterOddsChartFight } from "@/types/odds";
import { cn } from "@/lib/utils";
import { QualityBadge } from "./QualityBadge";

type FightSelectorProps = {
  fights: FighterOddsChartFight[];
  selectedId?: string;
  onSelect?: (fightId: string) => void;
};

export function FightSelector({
  fights,
  selectedId,
  onSelect,
}: FightSelectorProps) {
  if (!fights.length) {
    return (
      <p className="text-sm text-muted-foreground">
        No odds records available for this fighter yet.
      </p>
    );
  }

  return (
    <div className="grid gap-2" role="listbox" aria-label="Available fights">
      {fights.map((fight) => {
        const isSelected = fight.fight_id === selectedId;
        return (
          <button
            key={fight.fight_id}
            role="option"
            aria-selected={isSelected}
            onClick={() => onSelect?.(fight.fight_id)}
            className={cn(
              "relative flex w-full flex-col gap-2 rounded-xl border border-border/60 border-l-4 px-4 py-3 text-left transition hover:border-primary/40 hover:bg-muted/40",
              isSelected
                ? "border-l-primary bg-primary/10 shadow-inner ring-2 ring-primary/20"
                : "border-l-transparent",
            )}
          >
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold">
                  vs. {fight.opponent}
                </p>
                <p className="text-xs text-muted-foreground">
                  {fight.event} ·{" "}
                  {fight.event_date
                    ? format(new Date(fight.event_date), "LLL d, yyyy")
                    : "Date TBA"}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {isSelected ? (
                  <span className="rounded-full bg-primary/20 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider text-primary">
                    Selected
                  </span>
                ) : null}
                <QualityBadge tier={fight.quality} />
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
              <span>
                Opening:{" "}
                <strong className="text-foreground">
                  {fight.opening_odds ?? "—"}
                </strong>
              </span>
              <span>
                Closing:{" "}
                <strong className="text-foreground">
                  {fight.closing_odds ?? "—"}
                </strong>
              </span>
              <span>
                Points:{" "}
                <strong className="text-foreground">
                  {fight.num_odds_points}
                </strong>
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
