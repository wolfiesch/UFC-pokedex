"use client";

import FighterComparisonPanel from "@/components/Pokedex/FighterComparisonPanel";
import FighterDetailCard from "@/components/Pokedex/FighterDetailCard";
import { FighterLocationCard } from "@/components/fighter/FighterLocationCard";
import { useFighter } from "@/hooks/useFighter";
import type { FighterDetail } from "@/lib/types";

type FighterDetailPageClientProps = {
  fighterId: string;
  initialData?: FighterDetail;
};

export default function FighterDetailPageClient({
  fighterId,
  initialData,
}: FighterDetailPageClientProps) {
  const { fighter, isLoading, error, retry } = useFighter(
    fighterId,
    initialData,
  );

  return (
    <>
      <FighterDetailCard
        fighterId={fighterId}
        fighter={fighter}
        isLoading={isLoading}
        error={error}
        onRetry={retry}
      />
      {fighter && <FighterLocationCard fighter={fighter} />}
      {fighter ? (
        <FighterComparisonPanel
          primaryFighterId={fighterId}
          primaryFighterName={fighter.name}
        />
      ) : null}
    </>
  );
}
