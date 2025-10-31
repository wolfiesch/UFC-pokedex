"use client";

import Link from "next/link";

import type { FighterListItem } from "@/lib/types";

type Props = {
  favorites: FighterListItem[];
};

export default function FavoritesList({ favorites }: Props) {
  if (!favorites.length) {
    return <p className="text-slate-400">No favorites yet. Add fighters from the main list!</p>;
  }

  return (
    <ul className="space-y-4">
      {favorites.map((fighter) => (
        <li key={fighter.fighter_id} className="rounded-lg border border-slate-800 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-lg font-semibold text-pokedexYellow">{fighter.name}</p>
              {fighter.nickname && (
                <p className="text-sm text-slate-400">&quot;{fighter.nickname}&quot;</p>
              )}
            </div>
            <Link
              href={`/fighters/${fighter.fighter_id}`}
              className="text-sm text-pokedexBlue underline-offset-4 hover:underline"
            >
              View
            </Link>
          </div>
        </li>
      ))}
    </ul>
  );
}
