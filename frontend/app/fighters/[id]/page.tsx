"use client";

import { useParams } from "next/navigation";

import FighterComparisonPanel from "@/components/Pokedex/FighterComparisonPanel";
import FighterDetailCard from "@/components/Pokedex/FighterDetailCard";
import { useFighter } from "@/hooks/useFighter";

export default function FighterDetailPage() {
  const params = useParams<{ id: string }>();
  const fighterId = params?.id ?? "";
  const { fighter, isLoading } = useFighter(fighterId);

  return (
    <section className="mx-auto max-w-4xl space-y-8 px-4 py-12">
      <FighterDetailCard fighterId={fighterId} fighter={fighter} isLoading={isLoading} />
      {fighter ? (
        <FighterComparisonPanel
          primaryFighterId={fighterId}
          primaryFighterName={fighter.name}
        />
      ) : null}
    </section>
  );
}
