"use client";

import FighterComparisonPanel from "@/components/Pokedex/FighterComparisonPanel";
import FighterDetailCard from "@/components/Pokedex/FighterDetailCard";
import { useFighter } from "@/hooks/useFighter";

type FighterDetailPageClientProps = {
  fighterId: string;
};

export default function FighterDetailPageClient({
  fighterId,
}: FighterDetailPageClientProps) {
  const { fighter, isLoading, error, retry } = useFighter(fighterId);

  return (
    <>
      <FighterDetailCard
        fighterId={fighterId}
        fighter={fighter}
        isLoading={isLoading}
        error={error}
        onRetry={retry}
      />
      {fighter ? (
        <FighterComparisonPanel
          primaryFighterId={fighterId}
          primaryFighterName={fighter.name}
        />
      ) : null}
    </>
  );
}
