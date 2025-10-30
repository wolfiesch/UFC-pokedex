"use client";

import FighterCard from "./FighterCard";
import type { FighterListItem } from "@/lib/types";

type Props = {
  fighters: FighterListItem[];
  isLoading?: boolean;
};

export default function FighterGrid({ fighters, isLoading = false }: Props) {
  if (isLoading) {
    return <p className="text-slate-300">Loading fighters...</p>;
  }

  if (!fighters.length) {
    return <p className="text-slate-500">No fighters found. Try a different search.</p>;
  }

  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
      {fighters.map((fighter) => (
        <FighterCard key={fighter.fighter_id} fighter={fighter} />
      ))}
    </div>
  );
}
