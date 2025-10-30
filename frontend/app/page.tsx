"use client";

import FighterGrid from "@/components/FighterGrid";
import FilterPanel from "@/components/FilterPanel";
import SearchBar from "@/components/SearchBar";
import { useFighters } from "@/hooks/useFighters";
import { useSearch } from "@/hooks/useSearch";

export default function HomePage() {
  const { fighters, isLoading } = useFighters();
  const { stanceFilter, setStanceFilter } = useSearch();
  const stances = ["Orthodox", "Southpaw", "Switch", "Open Stance"];

  return (
    <section className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-4 py-12">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold text-pokedexYellow">UFC Fighter Pokedex</h1>
        <p className="text-slate-400">
          Browse UFC fighters, view stats, and curate your favorites.
        </p>
      </header>
      <SearchBar />
      <FilterPanel
        stances={stances}
        selectedStance={stanceFilter}
        onStanceChange={setStanceFilter}
      />
      <FighterGrid fighters={fighters} isLoading={isLoading} />
    </section>
  );
}
