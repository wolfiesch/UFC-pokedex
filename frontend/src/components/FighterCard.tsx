"use client";

import { memo, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { MapPin, Globe, Dumbbell } from "lucide-react";

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
import FighterImageFrame from "@/components/FighterImageFrame";
import { cn, resolveImageUrl } from "@/lib/utils";

type FighterCardProps = {
  fighter: FighterListItem;
};

function FighterCardComponent({ fighter }: FighterCardProps) {
  const { isFavorite: isFavoriteFn, toggleFavorite } = useFavorites({ autoInitialize: false });
  const isFavorite = isFavoriteFn(fighter.fighter_id);
  const imageSrc = resolveImageUrl(fighter.image_url);
  const [imageError, setImageError] = useState(false);
  const shouldShowImage = Boolean(imageSrc) && !imageError;
  /**
   * Placeholder styling mirrors the rounded interior of the FighterImageFrame so that
   * initials render with identical geometry to fetched portraits.
   */
  const placeholderClass =
    "flex h-full w-full items-center justify-center rounded-[1.18rem] text-white";

  const handleFavoriteClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const wasAdding = !isFavorite;
    const result = await toggleFavorite(fighter);

    // Show toast notification based on result
    if (result.success) {
      if (wasAdding) {
        toast.success(`Added ${fighter.name} to favorites`);
      } else {
        toast(`Removed ${fighter.name} from favorites`);
      }
    } else {
      toast.error(`Failed to update favorites: ${result.error}`);
    }
  };

  const isChampion = fighter.is_current_champion || fighter.is_former_champion;
  const championGlowClass = fighter.is_current_champion
    ? "ring-2 ring-yellow-500/60 shadow-[0_0_20px_rgba(234,179,8,0.3)]"
    : fighter.is_former_champion
    ? "ring-1 ring-amber-500/40 shadow-[0_0_12px_rgba(245,158,11,0.2)]"
    : "";

  return (
    <Link href={`/fighters/${fighter.fighter_id}`} className="group block h-full">
      <Card className={cn(
        "flex h-full flex-col overflow-hidden transition-transform hover:-translate-y-1 hover:shadow-xl",
        championGlowClass
      )}>
        <CardHeader className="p-6 pb-4">
          <div className="flex items-start justify-between gap-4 min-h-24">
            <div className="flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <CardTitle className="text-2xl group-hover:text-foreground/80">
                  {fighter.name}
                </CardTitle>
                {fighter.record ? (
                  <Badge variant="outline" className="text-xs font-mono">
                    {fighter.record}
                  </Badge>
                ) : null}
                {fighter.is_current_champion ? (
                  <Badge className="bg-gradient-to-r from-yellow-500 to-amber-600 text-white text-xs font-semibold border-0">
                    <svg
                      className="mr-1 h-3 w-3"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                    CURRENT CHAMP
                  </Badge>
                ) : fighter.is_former_champion ? (
                  <Badge variant="outline" className="text-xs font-semibold border-amber-600/50 text-amber-600 dark:text-amber-500">
                    <svg
                      className="mr-1 h-3 w-3"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                    FORMER CHAMP
                  </Badge>
                ) : null}
              </div>
              {fighter.nickname ? (
                <CardDescription className="text-sm tracking-tight line-clamp-1">
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
            <FighterImageFrame>
              {shouldShowImage ? (
                <img
                  src={imageSrc ?? ""}
                  alt={fighter.name}
                  className="h-full w-full scale-[1.01] object-contain drop-shadow-[0_18px_30px_rgba(15,23,42,0.45)] transition duration-700 ease-out group-hover/fighter-frame:scale-105 group-hover/fighter-frame:rotate-[0.8deg]"
                  loading="lazy"
                  onError={() => setImageError(true)}
                />
              ) : (
                <FighterImagePlaceholder
                  name={fighter.name}
                  division={fighter.division}
                  className={placeholderClass}
                />
              )}
            </FighterImageFrame>
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

          {/* Location Information - Desktop */}
          {((fighter as any).birthplace || (fighter as any).training_gym || (fighter as any).nationality) && (
            <div className="hidden md:flex flex-col gap-2 pt-2 border-t border-border/50">
              {(fighter as any).birthplace && (
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  <Badge variant="outline" className="text-xs">
                    <span className="text-muted-foreground">Born:</span>
                    <span className="ml-1 font-medium">{(fighter as any).birthplace}</span>
                  </Badge>
                </div>
              )}
              {(fighter as any).training_gym && (
                <div className="flex items-center gap-2">
                  <Dumbbell className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  <Badge variant="secondary" className="text-xs">
                    <span className="text-muted-foreground">Trains:</span>
                    <span className="ml-1 font-medium">{(fighter as any).training_gym}</span>
                  </Badge>
                </div>
              )}
              {!(fighter as any).birthplace && (fighter as any).nationality && (
                <div className="flex items-center gap-2">
                  <Globe className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  <Badge variant="outline" className="text-xs">
                    <span className="font-medium">{(fighter as any).nationality}</span>
                  </Badge>
                </div>
              )}
            </div>
          )}

          {/* Location Information - Mobile Compact */}
          {((fighter as any).birthplace || (fighter as any).training_gym || (fighter as any).nationality) && (
            <div className="flex md:hidden flex-wrap gap-1.5 pt-2 border-t border-border/50">
              {(fighter as any).birthplace && (
                <Badge variant="outline" className="text-xs">
                  📍 {(fighter as any).birthplace_city || (fighter as any).birthplace_country || (fighter as any).birthplace}
                </Badge>
              )}
              {(fighter as any).training_gym && (
                <Badge variant="secondary" className="text-xs">
                  💪 {(fighter as any).training_gym}
                </Badge>
              )}
              {!(fighter as any).birthplace && (fighter as any).nationality && (
                <Badge variant="outline" className="text-xs">
                  🌍 {(fighter as any).nationality}
                </Badge>
              )}
            </div>
          )}
        </CardContent>

        <CardFooter className="flex-wrap items-center justify-between gap-2 pt-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="uppercase tracking-tight">
              {fighter.division ?? "Unknown Division"}
            </Badge>
            {fighter.is_current_champion ? (
              <Badge className="bg-gradient-to-r from-yellow-500 to-amber-600 text-white text-xs font-semibold border-0">
                {fighter.was_interim ? "Current Champ (I)" : "Current Champ"}
              </Badge>
            ) : fighter.is_former_champion ? (
              <Badge variant="outline" className="text-xs font-semibold border-amber-600/50 text-amber-600 dark:text-amber-500">
                {fighter.was_interim ? "Former Champ (I)" : "Former Champ"}
              </Badge>
            ) : null}
          </div>
          <span className="text-xs font-medium uppercase tracking-[0.4em] text-muted-foreground">
            View →
          </span>
        </CardFooter>
      </Card>
    </Link>
  );
}

const fighterCardEqualityKeys: Array<keyof FighterListItem> = [
  "fighter_id",
  "name",
  "nickname",
  "record",
  "division",
  "image_url",
  "is_current_champion",
  "is_former_champion",
  "was_interim",
];

const areFighterCardPropsEqual = (
  prev: Readonly<FighterCardProps>,
  next: Readonly<FighterCardProps>
) => fighterCardEqualityKeys.every((key) => prev.fighter[key] === next.fighter[key]);

export default memo(FighterCardComponent, areFighterCardPropsEqual);
