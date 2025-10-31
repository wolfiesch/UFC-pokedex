"use client";

import FighterCard from "./FighterCard";
import type { FighterListItem } from "@/lib/types";

type Props = {
  fighters: FighterListItem[];
  isLoading?: boolean;
  error?: string | null;
};

export default function FighterGrid({ fighters, isLoading = false, error }: Props) {
  if (isLoading) {
    return <p className="text-slate-300">Loading fighters...</p>;
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-900/60 bg-red-950/40 p-4 text-sm text-red-200">
        Unable to load fighters right now. Error: {error}
      </div>
    );
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
