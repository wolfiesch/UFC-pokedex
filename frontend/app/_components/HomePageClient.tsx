"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import FighterGrid from "@/components/FighterGrid";
import FilterPanel from "@/components/FilterPanel";
import { useFighters } from "@/hooks/useFighters";
import { useSearch } from "@/hooks/useSearch";
import { getRandomFighter } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { PaginatedFightersResponse } from "@/lib/types";

const STANCES = ["Orthodox", "Southpaw", "Switch", "Open Stance"];
const DIVISIONS = [
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

const NATIONALITIES = [
  { code: "US", label: "United States" },
  { code: "BR", label: "Brazil" },
  { code: "IE", label: "Ireland" },
  { code: "RU", label: "Russia" },
  { code: "CA", label: "Canada" },
  { code: "GB", label: "United Kingdom" },
  { code: "MX", label: "Mexico" },
  { code: "AU", label: "Australia" },
  { code: "PL", label: "Poland" },
  { code: "FR", label: "France" },
  { code: "NL", label: "Netherlands" },
  { code: "SE", label: "Sweden" },
];

const NATIONALITY_LABELS = NATIONALITIES.reduce<Record<string, string>>(
  (acc, nationality) => {
    acc[nationality.code] = nationality.label;
    return acc;
  },
  {},
);

const CHAMPION_LABELS: Record<string, string> = {
  current: "Current champion",
  former: "Former champion",
};

type HomePageClientProps = {
  initialData?: PaginatedFightersResponse;
};

export default function HomePageClient({ initialData }: HomePageClientProps) {
  const router = useRouter();
  const {
    fighters,
    isLoading,
    isLoadingMore,
    error,
    total,
    hasMore,
    loadMore,
    retry,
  } = useFighters(initialData);
  const {
    searchTerm,
    stanceFilter,
    setStanceFilter,
    divisionFilter,
    setDivisionFilter,
    nationalityFilter,
    setNationalityFilter,
    championStatusFilters,
    toggleChampionStatusFilter,
    winStreakCount,
    lossStreakCount,
    setWinStreakCount,
    setLossStreakCount,
    resetFilters,
  } = useSearch();

  const handleRandomFighter = async () => {
    try {
      const fighter = await getRandomFighter();
      router.push(`/fighters/${fighter.fighter_id}`);
    } catch (err) {
      console.error("Failed to get random fighter:", err);
    }
  };

  const handleResetFilters = () => {
    resetFilters();
  };

  const filterSummaryParts = useMemo(() => {
    const parts: string[] = [];
    const trimmedSearch = searchTerm?.trim();
    if (trimmedSearch) {
      parts.push(`Search: “${trimmedSearch}”`);
    }
    if (divisionFilter) {
      parts.push(divisionFilter);
    }
    if (stanceFilter) {
      parts.push(stanceFilter);
    }
    if (nationalityFilter) {
      parts.push(
        NATIONALITY_LABELS[nationalityFilter] ?? nationalityFilter,
      );
    }
    if (championStatusFilters.length > 0) {
      championStatusFilters.forEach((status) => {
        parts.push(CHAMPION_LABELS[status] ?? status);
      });
    }
    if (winStreakCount !== null) {
      parts.push(`Win streak ≥ ${winStreakCount}`);
    }
    if (lossStreakCount !== null) {
      parts.push(`Losing streak ≥ ${lossStreakCount}`);
    }
    return parts;
  }, [
    searchTerm,
    divisionFilter,
    stanceFilter,
    nationalityFilter,
    championStatusFilters,
    winStreakCount,
    lossStreakCount,
  ]);

  const hasActiveFilters = filterSummaryParts.length > 0;
  const totalText = total && total > 0 ? total.toLocaleString() : "0";
  const filtersDescription = hasActiveFilters
    ? filterSummaryParts.join(", ")
    : "No filters applied";

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
            monochrome UI. Gotta smash em all.
          </p>
        </div>
      </header>
      <FilterPanel
        stances={STANCES}
        selectedStance={stanceFilter}
        onStanceChange={setStanceFilter}
        divisions={DIVISIONS}
        selectedDivision={divisionFilter}
        onDivisionChange={setDivisionFilter}
        nationalities={NATIONALITIES}
        selectedNationality={nationalityFilter}
        onNationalityChange={setNationalityFilter}
        championStatusFilters={championStatusFilters}
        onToggleChampionStatus={toggleChampionStatusFilter}
        winStreakCount={winStreakCount}
        lossStreakCount={lossStreakCount}
        onWinStreakChange={setWinStreakCount}
        onLossStreakChange={setLossStreakCount}
        isSearching={isLoading}
        onResetFilters={handleResetFilters}
      />
      <section
        className="flex flex-col gap-3 rounded-2xl border border-border bg-card/70 px-4 py-3 text-sm shadow-subtle md:flex-row md:items-center md:justify-between"
        aria-label="Roster summary"
      >
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
          <span className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground/80">
            Roster
          </span>
          <span className="font-medium text-foreground">
            {totalText} fighters
          </span>
          <span className="hidden text-muted-foreground md:inline">•</span>
          <span className="text-muted-foreground">
            Filters: {filtersDescription}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2 md:justify-end">
          {hasActiveFilters ? (
            <Button
              variant="ghost"
              size="sm"
              className="rounded-full"
              onClick={handleResetFilters}
            >
              Reset filters
            </Button>
          ) : null}
          <Button
            onClick={handleRandomFighter}
            size="sm"
            className="rounded-full"
          >
            🎲 Random Fighter
          </Button>
        </div>
      </section>
      <FighterGrid
        fighters={fighters}
        isLoading={isLoading}
        isLoadingMore={isLoadingMore}
        error={error}
        total={total}
        hasMore={hasMore}
        onLoadMore={loadMore}
        onRetry={retry}
        searchTerm={searchTerm}
        stanceFilter={stanceFilter}
        divisionFilter={divisionFilter}
        onClearFilters={handleResetFilters}
      />
    </section>
  );
}
