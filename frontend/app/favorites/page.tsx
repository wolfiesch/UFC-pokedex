import FavoritesDashboardClient from "./FavoritesDashboardClient";
import { getFavoriteCollectionDetail, getFavoriteCollections } from "@/lib/api";
import type {
  FavoriteCollectionDetail,
  FavoriteCollectionSummary,
} from "@/lib/types";

const DEFAULT_USER_ID = process.env.NEXT_PUBLIC_DEMO_FAVORITES_USER ?? "demo-user";

// Favorites depend on user-scoped data with no-store fetches; keep page dynamic.
export const dynamic = "force-dynamic";

/**
 * Server entrypoint for the favorites dashboard. We prefetch collection data so
 * the client component can hydrate instantly without an additional round-trip.
 */
export default async function FavoritesPage() {
  const userId = DEFAULT_USER_ID;

  let collections: FavoriteCollectionSummary[] = [];
  let detail: FavoriteCollectionDetail | null = null;

  try {
    const response = await getFavoriteCollections(userId);
    collections = response.collections;
    if (collections.length) {
      detail = await getFavoriteCollectionDetail(collections[0]?.id, userId);
    }
  } catch (error) {
    console.error("Failed to load favorites collections", error);
  }

  return (
    <div className="space-y-8 py-8">
      <FavoritesDashboardClient
        userId={userId}
        initialCollections={collections}
        initialDetail={detail}
      />
    </div>
  );
}
