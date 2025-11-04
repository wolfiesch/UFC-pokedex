import HomePageClient from "./_components/HomePageClient";
import { getFightersSSR } from "@/lib/api-ssr";

/**
 * Home page - Statically generated at build time
 * Fetches initial 20 fighters server-side for fast first paint
 * Client component handles search, filters, and pagination
 */
export default async function HomePage() {
  let initialData;

  try {
    // Fetch initial fighters at build time
    initialData = await getFightersSSR(20, 0);
  } catch (error) {
    console.error("Failed to fetch initial fighters:", error);
    // Fall back to client-side fetching if SSG fails
    initialData = undefined;
  }

  return <HomePageClient initialData={initialData} />;
}
