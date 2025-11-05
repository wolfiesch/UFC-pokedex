import { notFound } from "next/navigation";

import FighterDetailPageClient from "@/components/Pokedex/FighterDetailPageClient";
import { getAllFighterIdsSSR, getFighterSSR } from "@/lib/api-ssr";

// ISR: Revalidate every 24 hours (86400 seconds)
export const revalidate = 86400;

// Enable blocking fallback for fighters not pre-rendered
export const dynamicParams = true;

const PREFETCH_LIMIT = 500;
const SHOULD_PREFETCH_IN_DEV =
  process.env.NEXT_PREFETCH_FIGHTERS === "true";

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
  if (process.env.NODE_ENV === "development" && !SHOULD_PREFETCH_IN_DEV) {
    // Skip expensive prefetching while running turbopack locally unless opt-in
    return [];
  }

  try {
    const fighters = await getAllFighterIdsSSR(PREFETCH_LIMIT);
    return fighters
      .map(({ id }) => id?.trim())
      .filter((id): id is string => Boolean(id))
      .map((id) => ({ id }));
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
