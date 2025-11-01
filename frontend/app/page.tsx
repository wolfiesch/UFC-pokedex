"use client";

import { useRouter } from "next/navigation";
import FighterGrid from "@/components/FighterGrid";
import FilterPanel from "@/components/FilterPanel";
import SearchBar from "@/components/SearchBar";
import { useFighters } from "@/hooks/useFighters";
import { useSearch } from "@/hooks/useSearch";
import { getRandomFighter } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const { fighters, isLoading, error, total, offset, hasMore, nextPage, prevPage } =
    useFighters();
  const { stanceFilter, setStanceFilter } = useSearch();
  const stances = ["Orthodox", "Southpaw", "Switch", "Open Stance"];

  const handleRandomFighter = async () => {
    try {
      const fighter = await getRandomFighter();
      router.push(`/fighters/${fighter.fighter_id}`);
    } catch (err) {
      console.error("Failed to get random fighter:", err);
    }
  };

  return (
    <section className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-4 py-12">
      <header className="flex flex-col gap-4">
        <h1 className="text-3xl font-bold text-pokedexYellow">UFC Fighter Pokedex</h1>
        <p className="text-slate-400">
          Browse {total > 0 ? `${total} ` : ""}UFC fighters, view stats, and curate your
          favorites.
        </p>
        <button
          onClick={handleRandomFighter}
          className="w-fit rounded-lg bg-pokedexRed px-6 py-3 font-bold text-white transition-colors hover:bg-red-600"
        >
          🎲 Random Fighter
        </button>
      </header>
      <SearchBar />
      <FilterPanel
        stances={stances}
        selectedStance={stanceFilter}
        onStanceChange={setStanceFilter}
      />
      <FighterGrid
        fighters={fighters}
        isLoading={isLoading}
        error={error}
        total={total}
        offset={offset}
        hasMore={hasMore}
        onNextPage={nextPage}
        onPrevPage={prevPage}
      />
    </section>
  );
}
