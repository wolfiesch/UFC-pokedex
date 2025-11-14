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
    <div className="grid gap-2">
      {fights.map((fight) => {
        const isSelected = fight.fight_id === selectedId;
        return (
          <button
            key={fight.fight_id}
            onClick={() => onSelect?.(fight.fight_id)}
            className={cn(
              "flex w-full flex-col gap-2 rounded-xl border px-4 py-3 text-left transition hover:border-primary/40 hover:bg-muted/40",
              isSelected && "border-primary bg-primary/5 shadow-inner",
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
              <QualityBadge tier={fight.quality} />
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
