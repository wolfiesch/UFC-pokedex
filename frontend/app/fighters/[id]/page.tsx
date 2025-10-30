"use client";

import { useParams } from "next/navigation";

import FighterDetailCard from "@/components/Pokedex/FighterDetailCard";
import { useFighter } from "@/hooks/useFighter";

export default function FighterDetailPage() {
  const params = useParams<{ id: string }>();
  const fighterId = params?.id ?? "";
  const { fighter, isLoading } = useFighter(fighterId);

  return (
    <section className="mx-auto max-w-4xl px-4 py-12">
      <FighterDetailCard fighterId={fighterId} fighter={fighter} isLoading={isLoading} />
    </section>
  );
}
