"use client";

import FavoritesList from "@/components/FavoritesList";
import { useFavorites } from "@/hooks/useFavorites";

export default function FavoritesPage() {
  const { favorites } = useFavorites();
  return (
    <section className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="mb-4 text-3xl font-bold text-pokedexYellow">Favorites</h1>
      <FavoritesList favorites={favorites} />
    </section>
  );
}
