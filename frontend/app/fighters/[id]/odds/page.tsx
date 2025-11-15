import { notFound } from "next/navigation";

import { FighterOddsPageClient } from "@/components/odds/FighterOddsPageClient";
import { getAllFighterIdsSSR } from "@/lib/api-ssr";

export const revalidate = 600;

// Enable static params for export
export const dynamicParams = true;

type FighterOddsPageProps = {
  params: {
    id?: string;
  };
};

/**
 * Generate static params for fighter odds pages
 * Reuses the same fighter IDs from the main fighter detail page
 */
export async function generateStaticParams() {
  try {
    const fighters = await getAllFighterIdsSSR(500);
    const params = fighters.map(({ id }) => ({ id }));
    // For static export, ensure we have at least one param
    return params.length > 0 ? params : [{ id: "placeholder" }];
  } catch (error) {
    console.error("Failed to generate static params for fighter odds:", error);
    // For static export, return a placeholder to avoid build error
    return [{ id: "placeholder" }];
  }
}

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
