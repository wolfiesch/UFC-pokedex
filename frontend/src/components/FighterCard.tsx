"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";

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
import FighterImagePlaceholder from "@/components/FighterImagePlaceholder";
import { cn, resolveImageUrl } from "@/lib/utils";

type Props = {
  fighter: FighterListItem;
};

export default function FighterCard({ fighter }: Props) {
  const { favorites, toggleFavorite } = useFavorites();
  const isFavorite = favorites.some((fav) => fav.fighter_id === fighter.fighter_id);
  const imageSrc = resolveImageUrl(fighter.image_url);
  const [imageError, setImageError] = useState(false);
  const shouldShowImage = Boolean(imageSrc) && !imageError;
  const imageFrameClass =
    "relative flex aspect-[3/4] w-40 items-center justify-center overflow-hidden rounded-2xl border border-border/60";

  const handleFavoriteClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const wasAdding = !isFavorite;
    toggleFavorite(fighter);

    // Show toast notification
    if (wasAdding) {
      toast.success(`Added ${fighter.name} to favorites`);
    } else {
      toast(`Removed ${fighter.name} from favorites`);
    }
  };

  return (
    <Link href={`/fighters/${fighter.fighter_id}`} className="group block h-full">
      <Card className="flex h-full flex-col overflow-hidden transition-transform hover:-translate-y-1 hover:shadow-xl">
        <CardHeader className="p-6 pb-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <CardTitle className="text-2xl group-hover:text-foreground/80">
                  {fighter.name}
                </CardTitle>
                {fighter.record ? (
                  <Badge variant="outline" className="text-xs font-mono">
                    {fighter.record}
                  </Badge>
                ) : null}
              </div>
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
              className={cn(
                "group/fav transition-all",
                isFavorite && "hover:scale-105"
              )}
            >
              <svg
                className={cn(
                  "mr-1.5 h-4 w-4 transition-transform",
                  isFavorite
                    ? "fill-current group-hover/fav:scale-110"
                    : "fill-none group-hover/fav:scale-110"
                )}
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"
                />
              </svg>
              {isFavorite ? "Favorited" : "Favorite"}
            </Button>
          </div>
        </CardHeader>

        <CardContent className="flex flex-1 flex-col space-y-4">
          <div className="flex justify-center">
            {shouldShowImage ? (
              <div className={cn(imageFrameClass, "bg-muted/40")}>
                <img
                  src={imageSrc ?? ""}
                  alt={fighter.name}
                  className="h-full w-full object-contain"
                  loading="lazy"
                  onError={() => setImageError(true)}
                />
              </div>
            ) : (
              <FighterImagePlaceholder
                name={fighter.name}
                division={fighter.division}
                className={imageFrameClass}
              />
            )}
          </div>

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
