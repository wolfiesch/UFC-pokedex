"use client";

import { useMemo, useState, useTransition } from "react";
import { toast } from "sonner";

import CollectionsGrid from "@/components/favorites/CollectionsGrid";
import StatsSummary from "@/components/favorites/StatsSummary";
import ActivityFeed from "@/components/favorites/ActivityFeed";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type {
  FavoriteCollectionDetail,
  FavoriteCollectionSummary,
} from "@/lib/types";
import {
  getFavoriteCollectionDetail,
  reorderFavoriteEntries,
} from "@/lib/api";
import { exportFavoritesToCsv, exportFavoritesToPdf } from "@/lib/exports/favorites";

export type FavoritesDashboardClientProps = {
  /** Unique identifier for the currently authenticated user. */
  userId: string;
  /** List of collections returned from the initial server render. */
  initialCollections: any[];
  /** Fully-hydrated detail for the preselected collection. */
  initialDetail: any;
};

/**
 * Client-side wrapper responsible for wiring together data mutations,
 * drag-and-drop interactions, and export actions for the favorites dashboard.
 */
export function FavoritesDashboardClient({
  userId,
  initialCollections,
  initialDetail,
}: FavoritesDashboardClientProps) {
  const [collections, setCollections] = useState<any[]>(initialCollections);
  const [selectedDetail, setSelectedDetail] = useState<any>(initialDetail);
  const [isPending, startTransition] = useTransition();
  const [isReordering, setIsReordering] = useState(false);

  const selectedCollectionId = selectedDetail?.id ?? null;

  const selectedSummary = useMemo(() => {
    if (!selectedCollectionId) {
      return null;
    }
    return collections.find((collection) => collection.id === selectedCollectionId) ?? null;
  }, [collections, selectedCollectionId]);

  function handleSelectCollection(collection: FavoriteCollectionSummary) {
    startTransition(() => {
      getFavoriteCollectionDetail(collection.id, userId)
        .then((detail) => {
          setSelectedDetail(detail);
          setCollections((current) =>
            current.map((item) =>
              item.id === detail.id ? { ...item, stats: detail.stats } : item
            )
          );
        })
        .catch((error) => {
          console.error("Failed to load collection detail", error);
          toast.error("Unable to load favorites collection", {
            description: error instanceof Error ? error.message : "Unknown error",
          });
        });
    });
  }

  async function handleReorder(entryIds: number[]) {
    if (!selectedDetail) {
      return;
    }
    setIsReordering(true);
    try {
      const updated = await reorderFavoriteEntries(
        selectedDetail.id,
        { entry_ids: entryIds },
        userId
      );
      setSelectedDetail(updated);
      setCollections((current) =>
        current.map((collection) =>
          collection.id === updated.id ? { ...collection, stats: updated.stats } : collection
        )
      );
      toast.success("Favorites order updated");
    } catch (error) {
      console.error("Failed to reorder favorites", error);
      toast.error("Could not save new ordering", {
        description: error instanceof Error ? error.message : "Unexpected error",
      });
    } finally {
      setIsReordering(false);
    }
  }

  async function handleExportCsv() {
    if (!selectedDetail) {
      toast.warning("Select a collection before exporting");
      return;
    }
    await exportFavoritesToCsv(selectedDetail);
    toast.success("CSV download started");
  }

  async function handleExportPdf() {
    if (!selectedDetail) {
      toast.warning("Select a collection before exporting");
      return;
    }
    await exportFavoritesToPdf(selectedDetail);
    toast.info("PDF export is currently a placeholder. Check console for details.");
  }

  if (!collections.length) {
    return (
      <Card className="border-border/60 bg-card/80">
        <CardContent className="space-y-4 p-10 text-center">
          <h1 className="text-2xl font-semibold">Favorites dashboard</h1>
          <p className="text-sm text-muted-foreground">
            You have not created any collections yet. Visit fighter profiles to start curating your
            personal roster.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Favorites dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Manage custom fighter groupings, track performance, and export scouting notes.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="default" onClick={handleExportCsv} disabled={!selectedDetail}>
            Export CSV
          </Button>
          <Button variant="outline" onClick={handleExportPdf} disabled={!selectedDetail}>
            Export PDF
          </Button>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-4">
        <aside className="lg:col-span-1 space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Collections
          </h2>
          <div className="space-y-2">
            {collections.map((collection) => (
              <button
                key={collection.id}
                type="button"
                onClick={() => handleSelectCollection(collection)}
                disabled={isPending}
                className={cn(
                  "w-full rounded-xl border p-4 text-left transition",
                  "border-border/70 bg-card/70 hover:-translate-y-0.5 hover:bg-card",
                  collection.id === selectedCollectionId
                    ? "border-primary bg-primary/10"
                    : "border-border/60"
                )}
              >
                <p className="text-sm font-semibold text-foreground">{collection.title}</p>
                <p className="text-xs text-muted-foreground">{collection.description ?? "No description"}</p>
              </button>
            ))}
          </div>
        </aside>

        <main className="space-y-6 lg:col-span-3">
          {selectedDetail && selectedSummary ? (
            <>
              <StatsSummary collectionName={selectedSummary.title} stats={selectedDetail.stats} />
              <CollectionsGrid
                entries={selectedDetail.entries}
                onReorder={handleReorder}
                isReordering={isReordering}
              />
              <ActivityFeed activity={selectedDetail.activity} />
            </>
          ) : (
            <Card className="border-border/60 bg-card/80">
              <CardContent className="p-10 text-center text-sm text-muted-foreground">
                Select a collection to view stats, activity, and reorder fighters.
              </CardContent>
            </Card>
          )}
        </main>
      </div>
    </div>
  );
}

export default FavoritesDashboardClient;
