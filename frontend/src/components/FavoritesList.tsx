"use client";

import type { FighterListItem } from "@/lib/types";
import { FighterLink } from "@/components/fighter/FighterLink";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

type Props = {
  favorites: FighterListItem[];
};

export default function FavoritesList({ favorites }: Props) {
  if (!favorites.length) {
    return (
      <div className="rounded-3xl border border-border bg-card/60 p-6 text-center text-sm text-muted-foreground">
        No favorites yet. Add fighters from the main list!
      </div>
    );
  }

  return (
    <ul className="grid gap-4 md:grid-cols-2">
      {favorites.map((fighter) => (
        <li key={fighter.fighter_id}>
          <Card className="h-full border-border/80 bg-card/80 transition hover:-translate-y-1 hover:shadow-xl">
            <CardContent className="flex h-full flex-col justify-between gap-4 p-6">
              <div className="space-y-1">
                <FighterLink
                  fighterId={fighter.fighter_id}
                  name={fighter.name}
                  className="text-lg font-semibold"
                />
                {fighter.nickname ? (
                  <p className="text-sm text-muted-foreground">
                    &ldquo;{fighter.nickname}&rdquo;
                  </p>
                ) : null}
              </div>
              <div className="flex items-center justify-between">
                <Badge variant="outline" className="uppercase tracking-tight">
                  {fighter.division ?? "Unknown Division"}
                </Badge>
                <FighterLink
                  fighterId={fighter.fighter_id}
                  name={fighter.name}
                  className="inline-flex items-center text-sm font-medium text-foreground/70 transition hover:text-foreground"
                >
                  View profile →
                </FighterLink>
              </div>
            </CardContent>
          </Card>
        </li>
      ))}
    </ul>
  );
}
