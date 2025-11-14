import { notFound } from "next/navigation";

import { FighterOddsPageClient } from "@/components/odds/FighterOddsPageClient";

export const revalidate = 600;

type FighterOddsPageProps = {
  params: {
    id?: string;
  };
};

export default function FighterOddsPage({ params }: FighterOddsPageProps) {
  const fighterId = params.id?.trim();
  if (!fighterId) {
    notFound();
  }

  return (
    <div className="container max-w-5xl space-y-8 py-12">
      <FighterOddsPageClient fighterId={fighterId} />
    </div>
  );
}
