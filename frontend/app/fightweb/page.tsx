import type { Metadata } from "next";

import { FightWebClient } from "@/components/FightWeb";
import { DEFAULT_SORT } from "@/components/FightWeb/sort-utils";
import { Badge } from "@/components/ui/badge";
import { getFightGraph } from "@/lib/api";
import type { FightGraphQueryParams, FightGraphResponse } from "@/lib/types";

export const metadata: Metadata = {
  title: "FightWeb • UFC Fighter Pokedex",
  description:
    "Visualise UFC fighter connections through a graph of shared bouts and divisions.",
};

export const dynamic = "force-dynamic";

const DEFAULT_FILTERS: FightGraphQueryParams = {
  limit: 150,
  includeUpcoming: false,
  sortBy: DEFAULT_SORT,
};

export default async function FightWebPage() {
  let initialData: FightGraphResponse | null = null;
  let initialError: string | null = null;

  try {
    initialData = await getFightGraph(DEFAULT_FILTERS);
  } catch (error) {
    initialError =
      error instanceof Error
        ? error.message
        : "Unable to load the FightWeb network at this time.";
  }

  return (
    <section className="container flex flex-col gap-12 py-12">
      <header className="space-y-4">
        <Badge variant="outline" className="w-fit tracking-[0.35em]">
          Network
        </Badge>
        <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
          FightWeb
        </h1>
        <p className="max-w-2xl text-lg text-muted-foreground">
          Discover how UFC fighters are interconnected through shared bouts.
          The FightWeb network surfaces high-activity hubs, rivalries, and
          cross-division matchups in a single interactive view.
        </p>
      </header>

      <FightWebClient
        initialData={initialData}
        initialFilters={DEFAULT_FILTERS}
        initialError={initialError}
      />
    </section>
  );
}
