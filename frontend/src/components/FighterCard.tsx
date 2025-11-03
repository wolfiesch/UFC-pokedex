"use client";

import Link from "next/link";

import type { FighterListItem } from "@/lib/types";
import { useFavorites } from "@/hooks/useFavorites";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type Props = {
  fighter: FighterListItem;
};

export default function FighterCard({ fighter }: Props) {
  const { favorites, toggleFavorite } = useFavorites();
  const isFavorite = favorites.some((fav) => fav.fighter_id === fighter.fighter_id);

  const handleFavoriteClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    toggleFavorite(fighter);
  };

  return (
    <Link href={`/fighters/${fighter.fighter_id}`} className="group block h-full">
      <Card className="h-full overflow-hidden transition-transform hover:-translate-y-1 hover:shadow-xl">
        <CardHeader className="p-6 pb-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <CardTitle className="text-2xl group-hover:text-foreground/80">
                {fighter.name}
              </CardTitle>
              {fighter.nickname ? (
                <CardDescription className="text-sm tracking-tight">
                  &ldquo;{fighter.nickname}&rdquo;
                </CardDescription>
              ) : null}
            </div>
            <Button
              variant={isFavorite ? "default" : "outline"}
              size="sm"
              onClick={handleFavoriteClick}
            >
              {isFavorite ? "Favorited" : "Favorite"}
            </Button>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {fighter.image_url ? (
            <div className="flex justify-center">
              <div className="relative h-36 w-36 overflow-hidden rounded-2xl border border-border/60 bg-muted">
                <img
                  src={`${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/${fighter.image_url}`}
                  alt={fighter.name}
                  className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
                  onError={(event) => {
                    (event.target as HTMLImageElement).style.display = "none";
                  }}
                />
              </div>
            </div>
          ) : null}

          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                Height
              </dt>
              <dd className="text-base">{fighter.height ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                Weight
              </dt>
              <dd className="text-base">{fighter.weight ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                Reach
              </dt>
              <dd className="text-base">{fighter.reach ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                Stance
              </dt>
              <dd className="text-base">{fighter.stance ?? "—"}</dd>
            </div>
          </dl>
        </CardContent>

        <CardFooter className="items-center justify-between pt-0">
          <Badge variant="outline" className="uppercase tracking-tight">
            {fighter.division ?? "Unknown Division"}
          </Badge>
          <span className="text-xs font-medium uppercase tracking-[0.4em] text-muted-foreground">
            View →
          </span>
        </CardFooter>
      </Card>
    </Link>
  );
}
