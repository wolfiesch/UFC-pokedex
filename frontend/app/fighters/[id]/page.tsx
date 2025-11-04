import { notFound } from "next/navigation";

import FighterDetailPageClient from "@/components/Pokedex/FighterDetailPageClient";
import { getAllFighterIdsSSR, getFighterSSR } from "@/lib/api-ssr";

// ISR: Revalidate every 24 hours (86400 seconds)
export const revalidate = 86400;

// Enable blocking fallback for fighters not pre-rendered
export const dynamicParams = true;

type FighterDetailPageProps = {
  params: {
    id?: string;
  };
};

/**
 * Generate static params for top 500 fighters at build time
 * Others will be generated on-demand with ISR
 */
export async function generateStaticParams() {
  try {
    const fighters = await getAllFighterIdsSSR(500);
    return fighters;
  } catch (error) {
    console.error("Failed to generate static params:", error);
    // Return empty array to continue build without pre-rendering
    return [];
  }
}

export default async function FighterDetailPage({
  params,
}: FighterDetailPageProps) {
  const fighterId = params?.id?.trim();

  if (!fighterId) {
    notFound();
  }

  // Server-side data fetch for SSG/ISR
  let fighter;
  try {
    fighter = await getFighterSSR(fighterId);
  } catch (error) {
    // If fighter not found or fetch fails, show 404
    notFound();
  }

  return (
    <section className="container max-w-5xl space-y-10 py-12">
      <FighterDetailPageClient fighterId={fighterId} initialData={fighter} />
    </section>
  );
}
