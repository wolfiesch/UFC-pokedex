"use client";

import type { Metadata } from "next";
import { useEffect, useState } from "react";

import { FightWebClient } from "@/components/FightWeb";
import { DEFAULT_SORT } from "@/components/FightWeb/sort-utils";
import { Badge } from "@/components/ui/badge";
import { getFightGraph } from "@/lib/api";
import type { FightGraphQueryParams, FightGraphResponse } from "@/lib/types";

// Client-side only to avoid build-time API issues with empty fight graph data

const DEFAULT_FILTERS: FightGraphQueryParams = {
  limit: 150,
  includeUpcoming: false,
  sortBy: DEFAULT_SORT,
};

export default function FightWebPage() {
  const [initialData, setInitialData] = useState<FightGraphResponse | null>(null);
  const [initialError, setInitialError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadFightGraph() {
      try {
        const data = await getFightGraph(DEFAULT_FILTERS);
        setInitialData(data);
      } catch (error) {
        console.error("Failed to fetch fight graph:", error);
        setInitialError(
          error instanceof Error
            ? error.message
            : "Unable to load the FightWeb network at this time."
        );
      } finally {
        setLoading(false);
      }
    }

    loadFightGraph();
  }, []);

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

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-lg text-muted-foreground">Loading fight network...</div>
        </div>
      ) : (
        <FightWebClient
          initialData={initialData}
          initialFilters={DEFAULT_FILTERS}
          initialError={initialError}
        />
      )}
    </section>
  );
}
