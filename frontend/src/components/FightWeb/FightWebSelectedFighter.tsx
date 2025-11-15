"use client";

import { FighterLink } from "@/components/fighter/FighterLink";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import type { FightGraphResponse } from "@/lib/types";

type FightWebSelectedFighterProps = {
  selectedNode: FightGraphResponse["nodes"][number] | null;
  connections: {
    fighter: FightGraphResponse["nodes"][number];
    link: FightGraphResponse["links"][number];
  }[];
};

function formatNumber(value: number): string {
  return value.toLocaleString("en-US");
}

/**
 * Present detail for the currently focused fighter along with their top rivals.
 */
export function FightWebSelectedFighter({
  selectedNode,
  connections,
}: FightWebSelectedFighterProps) {
  if (!selectedNode) {
    return (
      <Card className="border border-dashed border-border/60 bg-card/40">
        <CardHeader>
          <CardTitle>Inspect fighters</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Click a node in the graph or search for a fighter to reveal their key
          connections.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border border-border/80 bg-card">
      <CardHeader>
        <CardTitle className="text-lg">
          <FighterLink
            fighterId={selectedNode.fighter_id}
            name={selectedNode.name}
          />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-muted-foreground">
        <div className="flex items-center justify-between">
          <span className="uppercase tracking-[0.3em] text-muted-foreground/80">
            Record
          </span>
          <span>{selectedNode.record ?? "Unknown"}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="uppercase tracking-[0.3em] text-muted-foreground/80">
            Division
          </span>
          <span>{selectedNode.division ?? "Unlisted"}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="uppercase tracking-[0.3em] text-muted-foreground/80">
            Total fights
          </span>
          <span>{formatNumber(selectedNode.total_fights)}</span>
        </div>
        {connections.length > 0 ? (
          <div className="space-y-2">
            <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground/80">
              Key connections
            </div>
            <ul className="space-y-2 text-sm">
              {connections.map(({ fighter, link }) => (
                <li
                  key={`${selectedNode.fighter_id}-${fighter.fighter_id}`}
                  className="flex items-center justify-between rounded-2xl border border-border/70 bg-background/50 px-3 py-2"
                >
                  <FighterLink
                    fighterId={fighter.fighter_id}
                    name={fighter.name}
                    className="text-base text-foreground/90"
                  />
                  <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
                    {link.fights} fights
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            Select a connected fighter in the graph to explore rivalries.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
