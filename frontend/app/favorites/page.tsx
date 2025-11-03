"use client";

import FavoritesList from "@/components/FavoritesList";
import { useFavorites } from "@/hooks/useFavorites";
import { Badge } from "@/components/ui/badge";

export default function FavoritesPage() {
  const { favorites } = useFavorites();
  return (
    <section className="container max-w-4xl space-y-6 py-12">
      <div className="space-y-3">
        <Badge variant="outline" className="tracking-[0.35em]">
          Collection
        </Badge>
        <h1 className="text-4xl font-semibold tracking-tight">Favorites</h1>
        <p className="text-muted-foreground">
          Your curated roster of fighters for quick access and comparison.
        </p>
      </div>
      <FavoritesList favorites={favorites} />
    </section>
  );
}
