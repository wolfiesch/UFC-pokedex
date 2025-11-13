"use client";

import { useEffect, useState } from "react";
import { format, isAfter, isWithinInterval, parseISO, startOfMonth, endOfMonth } from "date-fns";
import {
  CalendarDays,
  Clock,
  Filter,
  Flame,
  Globe2,
  LayoutGrid,
  List,
  MapPin,
  Sparkles,
  Tv,
} from "lucide-react";
import EventCard from "@/components/events/EventCard";
import EventSearch from "@/components/events/EventSearch";
import EventFilters from "@/components/events/EventFilters";
import EventTimeline from "@/components/events/EventTimeline";
import {
  detectEventType,
  getEventTypeConfig,
  normalizeEventType,
  type EventType,
} from "@/lib/event-utils";

interface Event {
  event_id: string;
  name: string;
  date: string;
  location: string | null;
  status: string;
  venue?: string | null;
  broadcast?: string | null;
  event_type?: EventType | null;
}

interface PaginatedEventsResponse {
  events: Event[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

interface FilterOptions {
  years: number[];
  locations: string[];
  event_types: string[];
}

const EVENTS_PER_PAGE = 20;

type ViewMode = "grid" | "timeline";

export default function EventsPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<"all" | "upcoming" | "completed">("all");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");

  // Search and filter state (multi-select capable)
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedYears, setSelectedYears] = useState<number[]>([]);
  const [selectedLocations, setSelectedLocations] = useState<string[]>([]);
  const [selectedEventTypes, setSelectedEventTypes] = useState<EventType[]>([]);

  // Filter options from API
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    years: [],
    locations: [],
    event_types: [],
  });

  const [showFilters, setShowFilters] = useState(false);
  const [upcomingEvents, setUpcomingEvents] = useState<Event[]>([]);

  // Fetch filter options on mount
  useEffect(() => {
    async function fetchFilterOptions() {
      try {
        // Use relative URL for client-side fetching - works with Next.js /api proxy
        const response = await fetch(`/api/events/filters/options`, { cache: "no-store" });

        if (response.ok) {
          const data = await response.json();
          setFilterOptions(data);
        }
      } catch (error) {
        console.error("Error fetching filter options:", error);
      }
    }

    fetchFilterOptions();
  }, []);

  useEffect(() => {
    async function fetchEvents() {
      setLoading(true);

      try {
        const hasFilters =
          Boolean(searchQuery) ||
          selectedYears.length > 0 ||
          selectedLocations.length > 0 ||
          selectedEventTypes.length > 0;

        const shouldAggregate =
          hasFilters &&
          (selectedYears.length > 1 ||
            selectedLocations.length > 1 ||
            selectedEventTypes.length > 1);

        if (shouldAggregate) {
          const yearValues = selectedYears.length > 0 ? selectedYears : [null];
          const locationValues = selectedLocations.length > 0 ? selectedLocations : [null];
          const typeValues = selectedEventTypes.length > 0 ? selectedEventTypes : [null];

          const combinations: Array<{
            year: number | null;
            location: string | null;
            eventType: EventType | null;
          }> = [];

          yearValues.forEach((yearValue) => {
            locationValues.forEach((locationValue) => {
              typeValues.forEach((typeValue) => {
                combinations.push({
                  year: yearValue ?? null,
                  location: locationValue ?? null,
                  eventType: typeValue ?? null,
                });
              });
            });
          });

          const settledResults = await Promise.allSettled(
            combinations.map(async ({ year, location, eventType }) => {
              const params = new URLSearchParams();
              params.set("limit", EVENTS_PER_PAGE.toString());
              if (searchQuery) params.set("q", searchQuery);
              if (year !== null) params.set("year", year.toString());
              if (location) params.set("location", location);
              if (eventType) params.set("event_type", eventType);
              if (statusFilter !== "all") params.set("status", statusFilter);

              const response = await fetch(`/api/events/search/?${params.toString()}`, { cache: "no-store" });
              if (!response.ok) {
                throw new Error(`Failed combination fetch: ${response.statusText}`);
              }

              const payload: PaginatedEventsResponse = await response.json();
              return payload.events ?? [];
            }),
          );

          const mergedEvents = new Map<string, Event>();
          settledResults.forEach((result) => {
            if (result.status === "fulfilled") {
              result.value.forEach((eventItem) => {
                mergedEvents.set(eventItem.event_id, eventItem);
              });
            } else {
              console.error("Failed to fetch combination", result.reason);
            }
          });

          const combined = Array.from(mergedEvents.values()).sort(
            (a, b) => parseISO(a.date).getTime() - parseISO(b.date).getTime(),
          );

          setEvents(combined);
          setTotal(combined.length);
          setOffset(0);
          return;
        }

        const params = new URLSearchParams();
        if (offset > 0) params.set("offset", offset.toString());
        params.set("limit", EVENTS_PER_PAGE.toString());

        let url: string;
        if (hasFilters) {
          url = `/api/events/search/`;
          if (searchQuery) params.set("q", searchQuery);
          if (selectedYears.length === 1) params.set("year", selectedYears[0]?.toString() ?? "");
          if (selectedLocations.length === 1) params.set("location", selectedLocations[0] ?? "");
          if (selectedEventTypes.length === 1) params.set("event_type", selectedEventTypes[0] ?? "");
          if (statusFilter !== "all") params.set("status", statusFilter);
          url = `${url}?${params.toString()}`;
        } else {
          if (statusFilter === "upcoming") {
            url = `/api/events/upcoming`;
          } else if (statusFilter === "completed") {
            url = `/api/events/completed?${params.toString()}`;
          } else {
            url = `/api/events/?${params.toString()}`;
          }
        }

        const response = await fetch(url, { cache: "no-store" });

        if (!response.ok) {
          throw new Error(`Failed to fetch events: ${response.statusText}`);
        }

        const data = await response.json();

        // Handle different response structures
        if (Array.isArray(data)) {
          // Upcoming events returns array directly
          setEvents(data);
          setTotal(data.length);
        } else {
          // Paginated responses
          setEvents(data.events || []);
          setTotal(data.total || 0);
        }
      } catch (error) {
        console.error("Error fetching events:", error);
        setEvents([]);
      } finally {
        setLoading(false);
      }
    }

    fetchEvents();
  }, [
    offset,
    statusFilter,
    searchQuery,
    selectedYears,
    selectedLocations,
    selectedEventTypes,
  ]);

  useEffect(() => {
    async function fetchUpcomingEvents() {
      try {
        const response = await fetch(`/api/events/upcoming`, { cache: "no-store" });

        if (!response.ok) {
          throw new Error(`Failed to fetch upcoming events: ${response.statusText}`);
        }

        const data: Event[] = await response.json();
        setUpcomingEvents(data);
      } catch (error) {
        console.error("Error fetching upcoming events:", error);
        setUpcomingEvents([]);
      }
    }

    fetchUpcomingEvents();
  }, []);

  const handleNextPage = () => {
    if (offset + EVENTS_PER_PAGE < total) {
      setOffset(offset + EVENTS_PER_PAGE);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handlePrevPage = () => {
    if (offset >= EVENTS_PER_PAGE) {
      setOffset(offset - EVENTS_PER_PAGE);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handleFilterChange = (newFilter: "all" | "upcoming" | "completed") => {
    setStatusFilter(newFilter);
    setOffset(0); // Reset to first page
  };

  const handleSearchChange = (query: string) => {
    setSearchQuery(query);
    setOffset(0);
  };

  const handleYearsChange = (years: number[]) => {
    setSelectedYears(years);
    setOffset(0);
  };

  const handleLocationsChange = (locations: string[]) => {
    setSelectedLocations(locations);
    setOffset(0);
  };

  const handleEventTypesChange = (eventTypes: EventType[]) => {
    setSelectedEventTypes(eventTypes);
    setOffset(0);
  };

  const clearAllFilters = () => {
    setSelectedYears([]);
    setSelectedLocations([]);
    setSelectedEventTypes([]);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-white">
        <div className="mx-auto flex min-h-screen max-w-7xl flex-col items-center justify-center gap-6 px-4">
          <div className="h-12 w-12 animate-spin rounded-full border-2 border-white/30 border-t-emerald-400" />
          <p className="text-lg font-semibold tracking-[0.3em] text-white/70">Calibrating octagon feed…</p>
        </div>
      </div>
    );
  }

  const hasActiveFilters =
    Boolean(searchQuery) ||
    selectedYears.length > 0 ||
    selectedLocations.length > 0 ||
    selectedEventTypes.length > 0;

  const nextPayPerView = (() => {
    const ppvCandidates = upcomingEvents
      .map((eventItem) => ({
        eventItem,
        normalizedType:
          normalizeEventType(eventItem.event_type ?? null) ?? detectEventType(eventItem.name),
      }))
      .filter(({ normalizedType }) => normalizedType === "ppv")
      .sort(
        (a, b) => parseISO(a.eventItem.date).getTime() - parseISO(b.eventItem.date).getTime(),
      );

    return ppvCandidates.length > 0 ? ppvCandidates[0]?.eventItem ?? null : null;
  })();

  const nextPpvTypeConfig = nextPayPerView
    ? getEventTypeConfig(
        normalizeEventType(nextPayPerView.event_type ?? null) ?? detectEventType(nextPayPerView.name),
      )
    : null;

  const uniqueCountriesCount = (() => {
    const countrySet = new Set<string>();

    filterOptions.locations.forEach((location) => {
      const fragments = location.split(",");
      const country = fragments[fragments.length - 1]?.trim();
      if (country) {
        countrySet.add(country);
      }
    });

    return countrySet.size;
  })();

  const thisMonthUpcomingCount = (() => {
    const timeWindow = {
      start: startOfMonth(new Date()),
      end: endOfMonth(new Date()),
    };

    return upcomingEvents.filter((eventItem) => {
      const eventDate = parseISO(eventItem.date);
      return isWithinInterval(eventDate, timeWindow);
    }).length;
  })();

  const nextEventCountdown = (() => {
    if (!nextPayPerView) {
      return null;
    }

    const now = new Date();
    const eventDate = parseISO(nextPayPerView.date);

    if (!isAfter(eventDate, now)) {
      return "Live now";
    }

    const diffMs = eventDate.getTime() - now.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor((diffMs / (1000 * 60 * 60)) % 24);

    if (diffDays <= 0) {
      return `${diffHours}h to go`;
    }

    return `${diffDays}d ${diffHours}h to go`;
  })();

  const showPagination = statusFilter !== "upcoming" && total > EVENTS_PER_PAGE && !hasActiveFilters;

  return (
    <div className="relative min-h-screen bg-slate-950/95">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(148,163,184,0.16),transparent_55%)]" />
      <div className="relative z-10 mx-auto max-w-7xl px-4 pb-16">
        <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-900/60 shadow-[0_25px_70px_-30px_rgba(15,23,42,1)]">
          <div
            className="absolute inset-0"
            aria-hidden="true"
            style={{
              backgroundImage:
                "linear-gradient(135deg, rgba(15,23,42,0.95) 0%, rgba(15,23,42,0.55) 60%, rgba(15,23,42,0.85) 100%), url('https://images.unsplash.com/photo-1577401132921-10b8d2fc97b0?auto=format&fit=crop&w=1600&q=80')",
              backgroundSize: "cover",
              backgroundPosition: "center",
            }}
          />
          <div className="absolute inset-0 bg-gradient-to-r from-slate-950/80 via-slate-950/40 to-slate-950/80" aria-hidden="true" />
          <div className="relative flex flex-col gap-10 px-8 py-12 sm:px-12 lg:flex-row lg:items-center">
            <div className="flex-1 space-y-6 text-slate-200">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-white/80 backdrop-blur">
                <Flame className="h-4 w-4 text-amber-300" aria-hidden="true" />
                UFC Events Command Center
              </div>
              <div>
                <h1 className="text-4xl font-black text-white drop-shadow-md sm:text-5xl">
                  Step inside the Octagon Archive
                </h1>
                <p className="mt-4 max-w-2xl text-base text-slate-200/80">
                  Track every UFC battle from the first bell to the next blockbuster night. Search, filter, and
                  relive legendary moments with a cinematic dashboard built for fight fans and analysts alike.
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-white/60">
                    <Sparkles className="h-4 w-4 text-amber-300" aria-hidden="true" />
                    Indexed Events
                  </div>
                  <p className="mt-3 text-3xl font-black text-white">{total.toLocaleString()}</p>
                  <p className="text-xs uppercase tracking-[0.3em] text-white/50">Complete history</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-white/60">
                    <Globe2 className="h-4 w-4 text-sky-300" aria-hidden="true" />
                    Countries Hosted
                  </div>
                  <p className="mt-3 text-3xl font-black text-white">{uniqueCountriesCount}</p>
                  <p className="text-xs uppercase tracking-[0.3em] text-white/50">Global footprint</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-white/60">
                    <CalendarDays className="h-4 w-4 text-emerald-300" aria-hidden="true" />
                    This Month
                  </div>
                  <p className="mt-3 text-3xl font-black text-white">{thisMonthUpcomingCount}</p>
                  <p className="text-xs uppercase tracking-[0.3em] text-white/50">Upcoming cards</p>
                </div>
              </div>
            </div>
            <div className="w-full max-w-md rounded-3xl border border-white/10 bg-black/30 p-6 backdrop-blur-lg">
              <div className="flex items-center justify-between gap-2 text-sm font-medium text-white/70">
                <div className="flex items-center gap-2">
                  <Flame className="h-4 w-4 text-amber-400" aria-hidden="true" />
                  Next PPV Spotlight
                </div>
                {nextPpvTypeConfig && (
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${nextPpvTypeConfig.badgeClass}`}
                  >
                    {nextPpvTypeConfig.label}
                  </span>
                )}
              </div>
              {nextPayPerView ? (
                <div className="mt-4 space-y-5 text-white">
                  <div>
                    <p className="text-sm uppercase tracking-[0.3em] text-amber-300/80">Featured Event</p>
                    <h2 className="mt-2 text-2xl font-black leading-tight">{nextPayPerView.name}</h2>
                  </div>
                  <div className="grid gap-3 text-sm text-white/80">
                    <div className="flex items-center gap-2">
                      <CalendarDays className="h-4 w-4 text-white/60" aria-hidden="true" />
                      <span>{format(parseISO(nextPayPerView.date), "MMMM d, yyyy")}</span>
                    </div>
                    {nextPayPerView.location && (
                      <div className="flex items-center gap-2">
                        <MapPin className="h-4 w-4 text-white/60" aria-hidden="true" />
                        <span>{nextPayPerView.location}</span>
                      </div>
                    )}
                    {nextPayPerView.broadcast && (
                      <div className="flex items-center gap-2">
                        <Tv className="h-4 w-4 text-white/60" aria-hidden="true" />
                        <span>{nextPayPerView.broadcast}</span>
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-emerald-300" aria-hidden="true" />
                      <span className="font-semibold text-emerald-200">{nextEventCountdown}</span>
                    </div>
                  </div>
                  <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-100/90">
                    <p className="font-semibold uppercase tracking-[0.3em]">Key Storyline</p>
                    <p className="mt-2 leading-relaxed">
                      Every championship night writes a new chapter. Dive into the full fight card, tale-of-the-tape
                      analytics, and historical context before the first punch lands.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <a
                      href={`/events/${nextPayPerView.event_id}`}
                      className="inline-flex items-center justify-center gap-2 rounded-full bg-amber-400/90 px-5 py-2 text-sm font-semibold text-slate-900 shadow-lg shadow-amber-500/30 transition hover:bg-amber-300"
                    >
                      See Fight Card
                      <Flame className="h-4 w-4" aria-hidden="true" />
                    </a>
                    <button
                      onClick={() => handleFilterChange("upcoming")}
                      className="inline-flex items-center justify-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:border-white/40 hover:bg-white/20"
                    >
                      Track Upcoming
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mt-6 rounded-2xl border border-dashed border-white/20 bg-white/5 p-6 text-center text-sm text-white/70">
                  No pay-per-view events announced yet. Check back soon as the matchmakers finalize the next blockbuster card.
                </div>
              )}
            </div>
          </div>
          <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-slate-950/95 via-transparent to-transparent" aria-hidden="true" />
        </section>

        <div className="mt-10 space-y-6">
          <div className="sticky top-4 z-20">
            <div className="rounded-3xl border border-white/10 bg-white/10 shadow-[0_10px_40px_rgba(15,23,42,0.35)] backdrop-blur-xl">
              <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
                <div className="flex w-full flex-col gap-3 sm:flex-row sm:items-center">
                  <EventSearch
                    value={searchQuery}
                    onChange={handleSearchChange}
                    placeholder="Search by event, city, headliner, or broadcast"
                  />
                  <div className="flex items-center gap-2">
                    <div className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1 text-xs font-semibold text-white/80">
                      <button
                        onClick={() => handleFilterChange("all")}
                        className={`flex items-center gap-1 rounded-full px-3 py-1 transition ${
                          statusFilter === "all" ? "bg-white text-slate-900 shadow" : "hover:bg-white/10"
                        }`}
                      >
                        <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                        All
                      </button>
                      <button
                        onClick={() => handleFilterChange("upcoming")}
                        className={`flex items-center gap-1 rounded-full px-3 py-1 transition ${
                          statusFilter === "upcoming" ? "bg-emerald-300 text-slate-900 shadow" : "hover:bg-white/10"
                        }`}
                      >
                        <Flame className="h-3.5 w-3.5" aria-hidden="true" />
                        Upcoming
                      </button>
                      <button
                        onClick={() => handleFilterChange("completed")}
                        className={`flex items-center gap-1 rounded-full px-3 py-1 transition ${
                          statusFilter === "completed" ? "bg-blue-200 text-slate-900 shadow" : "hover:bg-white/10"
                        }`}
                      >
                        <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />
                        Completed
                      </button>
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between gap-3 sm:justify-end">
                  <button
                    onClick={() => setShowFilters((prev) => !prev)}
                    className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition ${
                      showFilters || hasActiveFilters
                        ? "border-emerald-300/60 bg-emerald-400/10 text-emerald-100"
                        : "border-white/10 bg-white/5 text-white hover:border-white/30 hover:bg-white/10"
                    }`}
                  >
                    <Filter className="h-4 w-4" aria-hidden="true" />
                    Advanced Filters
                    {hasActiveFilters && (
                      <span className="inline-flex items-center rounded-full bg-emerald-400/90 px-2 py-0.5 text-xs font-semibold text-slate-900">
                        Active
                      </span>
                    )}
                  </button>
                  <div className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1 text-xs font-semibold text-white/80">
                    <button
                      onClick={() => setViewMode("grid")}
                      className={`flex items-center gap-1 rounded-full px-3 py-1 transition ${
                        viewMode === "grid" ? "bg-white text-slate-900 shadow" : "hover:bg-white/10"
                      }`}
                      title="Grid view"
                    >
                      <LayoutGrid className="h-3.5 w-3.5" aria-hidden="true" />
                      Grid
                    </button>
                    <button
                      onClick={() => setViewMode("timeline")}
                      className={`flex items-center gap-1 rounded-full px-3 py-1 transition ${
                        viewMode === "timeline" ? "bg-white text-slate-900 shadow" : "hover:bg-white/10"
                      }`}
                      title="Timeline view"
                    >
                      <List className="h-3.5 w-3.5" aria-hidden="true" />
                      Timeline
                    </button>
                  </div>
                </div>
              </div>
              {showFilters && (
                <div className="border-t border-white/10 p-4">
                  <EventFilters
                    years={filterOptions.years}
                    locations={filterOptions.locations}
                    selectedYears={selectedYears}
                    selectedLocations={selectedLocations}
                    selectedEventTypes={selectedEventTypes}
                    onYearsChange={handleYearsChange}
                    onLocationsChange={handleLocationsChange}
                    onEventTypesChange={handleEventTypesChange}
                    onClearAll={clearAllFilters}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="relative z-10 mx-auto mt-12 max-w-7xl px-4 pb-24">
        {viewMode === "grid" ? (
          <div className="grid grid-cols-1 gap-6">
            {events.map((event) => (
              <EventCard key={event.event_id} event={event} />
            ))}
          </div>
        ) : (
          <EventTimeline events={events} />
        )}

        {showPagination && (
          <div className="mt-12 flex items-center justify-center gap-4">
            <button
              onClick={handlePrevPage}
              disabled={offset === 0}
              className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-white transition hover:border-white/30 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={handleNextPage}
              disabled={offset + EVENTS_PER_PAGE >= total}
              className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-white transition hover:border-white/30 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
