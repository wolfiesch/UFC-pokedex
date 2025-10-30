"use client";

import Link from "next/link";

import type { FighterListItem } from "@/lib/types";
import { useFavorites } from "@/hooks/useFavorites";

type Props = {
  fighter: FighterListItem;
};

export default function FighterCard({ fighter }: Props) {
  const { favorites, toggleFavorite } = useFavorites();
  const isFavorite = favorites.some((fav) => fav.fighter_id === fighter.fighter_id);

  return (
    <article className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 shadow-lg transition hover:border-pokedexYellow/60 hover:shadow-pokedexYellow/30">
      <header className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-pokedexYellow">{fighter.name}</h2>
        <button
          type="button"
          onClick={() => toggleFavorite(fighter)}
          className="rounded-full border border-pokedexYellow px-3 py-1 text-xs uppercase tracking-wide text-pokedexYellow hover:bg-pokedexYellow hover:text-slate-950"
        >
          {isFavorite ? "Remove" : "Favorite"}
        </button>
      </header>
      {fighter.nickname && <p className="text-sm text-slate-400">"{fighter.nickname}"</p>}
      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-300">
        <div>
          <dt className="font-semibold text-slate-100">Height</dt>
          <dd>{fighter.height ?? "—"}</dd>
        </div>
        <div>
          <dt className="font-semibold text-slate-100">Weight</dt>
          <dd>{fighter.weight ?? "—"}</dd>
        </div>
        <div>
          <dt className="font-semibold text-slate-100">Reach</dt>
          <dd>{fighter.reach ?? "—"}</dd>
        </div>
        <div>
          <dt className="font-semibold text-slate-100">Stance</dt>
          <dd>{fighter.stance ?? "—"}</dd>
        </div>
      </dl>
      <footer className="mt-4 flex items-center justify-between text-xs text-pokedexBlue">
        <span>{fighter.division ?? "Unknown Division"}</span>
        <Link
          href={`/fighters/${fighter.fighter_id}`}
          className="underline-offset-2 hover:underline"
        >
          View details →
        </Link>
      </footer>
    </article>
  );
}
