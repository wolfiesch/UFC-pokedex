"use client";

import { useRouter } from "next/navigation";
import FighterGrid from "@/components/FighterGrid";
import FilterPanel from "@/components/FilterPanel";
import SearchBar from "@/components/SearchBar";
import { useFighters } from "@/hooks/useFighters";
import { useSearch } from "@/hooks/useSearch";
import { getRandomFighter } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { PaginatedFightersResponse } from "@/lib/types";

type HomePageClientProps = {
  initialData?: PaginatedFightersResponse;
};

export default function HomePageClient({ initialData }: HomePageClientProps) {
  const router = useRouter();
  const {
    fighters,
    isLoading,
    isFetchingPage,
    error,
    total,
    limit,
    offset,
    canNextPage,
    canPreviousPage,
    goToNextPage,
    goToPreviousPage,
    setLimit,
    resetPagination,
    retry,
  } = useFighters(initialData);
  const {
    searchTerm,
    setSearchTerm,
    stanceFilter,
    setStanceFilter,
    divisionFilter,
    setDivisionFilter,
  } = useSearch();
  const stances = ["Orthodox", "Southpaw", "Switch", "Open Stance"];
  const divisions = [
    "Bantamweight",
    "Featherweight",
    "Flyweight",
    "Heavyweight",
    "Light Heavyweight",
    "Lightweight",
    "Middleweight",
    "Strawweight",
    "Super Heavyweight",
    "Welterweight",
  ];

  const handleRandomFighter = async () => {
    try {
      const fighter = await getRandomFighter();
      router.push(`/fighters/${fighter.fighter_id}`);
    } catch (err) {
      console.error("Failed to get random fighter:", err);
    }
  };

  return (
    <section className="container flex flex-col gap-10 py-12">
      <header className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <Badge variant="outline" className="w-fit tracking-[0.35em]">
            Roster
          </Badge>
          <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
            UFC Fighter Pokedex
          </h1>
          <p className="max-w-2xl text-lg text-muted-foreground">
            Browse{" "}
            {total > 0 ? `${total.toLocaleString()} ` : ""}UFC fighters,
            explore their profiles, and curate your favourites in a streamlined
            monochrome UI.
          </p>
        </div>
        <Button
          onClick={handleRandomFighter}
          size="lg"
          className="w-full justify-center sm:w-fit"
        >
          🎲 Random Fighter
        </Button>
      </header>
      <SearchBar
        isLoading={isLoading || isFetchingPage}
        pageSize={limit}
        onPageSizeChange={setLimit}
        onSearchChange={() => {
          resetPagination();
        }}
      />
      <FilterPanel
        stances={stances}
        selectedStance={stanceFilter}
        onStanceChange={setStanceFilter}
        divisions={divisions}
        selectedDivision={divisionFilter}
        onDivisionChange={setDivisionFilter}
      />
      <FighterGrid
        fighters={fighters}
        isLoading={isLoading}
        isFetchingPage={isFetchingPage}
        error={error}
        total={total}
        limit={limit}
        offset={offset}
        canNextPage={canNextPage}
        canPreviousPage={canPreviousPage}
        onNextPage={goToNextPage}
        onPreviousPage={goToPreviousPage}
        onRetry={retry}
        searchTerm={searchTerm}
        stanceFilter={stanceFilter}
        divisionFilter={divisionFilter}
        onClearFilters={() => {
          setSearchTerm("");
          setStanceFilter(null);
          setDivisionFilter(null);
          resetPagination();
        }}
      />
    </section>
  );
}
