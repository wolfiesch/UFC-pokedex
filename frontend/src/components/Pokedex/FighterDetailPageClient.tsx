"use client";

import { Suspense } from "react";
import dynamic from "next/dynamic";

import { useFighter } from "@/hooks/useFighter";
import type { FighterDetail } from "@/lib/types";

const FighterDetailCard = dynamic(
  () => import("@/components/Pokedex/FighterDetailCard"),
  { ssr: false, suspense: true }
);

const FighterComparisonPanel = dynamic(
  () => import("@/components/Pokedex/FighterComparisonPanel"),
  { ssr: false, suspense: true }
);

const detailFallback = (
  <div className="rounded-xl border border-border/60 bg-card/40 p-6 text-muted-foreground">
    Loading fighter profile…
  </div>
);

const comparisonFallback = (
  <div className="rounded-xl border border-border/60 bg-card/40 p-6 text-muted-foreground">
    Loading comparison tools…
  </div>
);

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
    initialData
  );

  return (
    <>
      <Suspense fallback={detailFallback}>
        <FighterDetailCard
          fighterId={fighterId}
          fighter={fighter}
          isLoading={isLoading}
          error={error}
          onRetry={retry}
        />
      </Suspense>
      {fighter ? (
        <Suspense fallback={comparisonFallback}>
          <FighterComparisonPanel
            primaryFighterId={fighterId}
            primaryFighterName={fighter.name}
          />
        </Suspense>
      ) : null}
    </>
  );
}
