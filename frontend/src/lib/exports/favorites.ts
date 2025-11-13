"use client";

import type { FavoriteCollectionDetail, FavoriteEntry } from "@/lib/types";

/**
 * Serialize the fighters in a collection into a CSV string.
 */
export function serializeFavoritesToCsv(
  collection: FavoriteCollectionDetail,
): string {
  const header = [
    "Fighter ID",
    "Notes",
    "Tags",
    "Position",
    "Created At",
    "Updated At",
  ].join(",");

  const rows = collection.entries.map((entry: FavoriteEntry) => {
    const tags = entry.tags.join("|");
    const safeNotes = entry.notes?.replace(/"/g, '""') ?? "";
    return [
      entry.fighter_id,
      `"${safeNotes}"`,
      `"${tags}"`,
      String(entry.position),
      entry.created_at,
      entry.updated_at,
    ].join(",");
  });

  return [header, ...rows].join("\n");
}

/**
 * Trigger a CSV download in the browser for the supplied collection.
 */
export async function exportFavoritesToCsv(
  collection: FavoriteCollectionDetail,
): Promise<void> {
  const csv = serializeFavoritesToCsv(collection);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${collection.slug ?? collection.title}.csv`;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

/**
 * TODO: Replace this stub once a dedicated PDF export endpoint is available.
 * For now we simply log a message so the UI can surface user feedback.
 */
export async function exportFavoritesToPdf(
  collection: FavoriteCollectionDetail,
): Promise<void> {
  // Stub: PDF export not yet implemented.
}
