import { notFound } from "next/navigation";

import FighterDetailPageClient from "@/components/Pokedex/FighterDetailPageClient";

type FighterDetailPageProps = {
  params: {
    id?: string;
  };
};

export default function FighterDetailPage({ params }: FighterDetailPageProps) {
  const fighterId = params?.id?.trim();

  if (!fighterId) {
    notFound();
  }

  return (
    <section className="container max-w-5xl space-y-10 py-12">
      <FighterDetailPageClient fighterId={fighterId} />
    </section>
  );
}
