"use client";

import { useState, useEffect, useMemo } from "react";
import { format, parseISO, formatDistanceStrict, isSameMonth } from "date-fns";
import EventCard from "@/components/events/EventCard";
import EventSearch from "@/components/events/EventSearch";
import EventFilters from "@/components/events/EventFilters";
import EventTimeline from "@/components/events/EventTimeline";
import { detectEventType, normalizeEventType, type EventType, EVENT_TYPE_CONFIGS } from "@/lib/event-utils";
import {
  Sparkles,
  Filter,
  ListFilter,
  MapPin,
  CalendarDays,
  Circle,
  Rows2,
  LineChart,
  Target,
  Layers,
  History,
} from "lucide-react";

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

  // Search and filter state
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
  const [nextHeadlineEvent, setNextHeadlineEvent] = useState<Event | null>(null);
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
        // Build query parameters
        const params = new URLSearchParams();
        if (offset > 0) params.set("offset", offset.toString());
        params.set("limit", EVENTS_PER_PAGE.toString());

        // Determine which endpoint to use
        // Use relative URLs for client-side fetching - works with Next.js /api proxy
        let url: string;
        const hasFilters =
          searchQuery ||
          selectedYears.length > 0 ||
          selectedLocations.length > 0 ||
          selectedEventTypes.length > 0;

        if (hasFilters) {
          // Use search endpoint with filters
          url = `/api/events/search/`;
          if (searchQuery) params.set("q", searchQuery);
          if (selectedYears.length > 0) params.set("year", selectedYears.join(","));
          if (selectedLocations.length > 0) params.set("location", selectedLocations.join(","));
          if (selectedEventTypes.length > 0) params.set("event_type", selectedEventTypes.join(","));
          if (statusFilter !== "all") params.set("status", statusFilter);
        } else {
          // Use regular list endpoints
          if (statusFilter === "upcoming") {
            url = `/api/events/upcoming`;
          } else if (statusFilter === "completed") {
            url = `/api/events/completed?${params.toString()}`;
          } else {
            url = `/api/events/?${params.toString()}`;
          }
        }

        if (hasFilters) {
          url = `${url}?${params.toString()}`;
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
    async function fetchUpcomingShowcase() {
      try {
        const response = await fetch(`/api/events/upcoming`, { cache: "no-store" });
        if (!response.ok) {
          throw new Error("Failed to fetch upcoming events");
        }
        const data: Event[] = await response.json();
        setUpcomingEvents(data);

        const marquee = data
          .filter((event) => {
            const type = normalizeEventType(event.event_type ?? null) ?? detectEventType(event.name);
            return type === "ppv";
          })
          .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())[0];
        setNextHeadlineEvent(marquee ?? data[0] ?? null);
      } catch (error) {
        console.error("Error fetching upcoming events:", error);
      }
    }

    fetchUpcomingShowcase();
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

  const handleClearAllFilters = () => {
    setSelectedYears([]);
    setSelectedLocations([]);
    setSelectedEventTypes([]);
    setOffset(0);
  };

  const heroEvent = nextHeadlineEvent ?? events[0] ?? null;

  const heroStats = useMemo(() => {
    const countrySet = new Set<string>();
    filterOptions.locations.forEach((location) => {
      const parts = location.split(",");
      const country = parts[parts.length - 1]?.trim();
      if (country) countrySet.add(country);
    });

    const now = new Date();
    const monthlyUpcoming = upcomingEvents.filter((event) => {
      const date = new Date(event.date);
      return isSameMonth(date, now);
    }).length;

    return [
      {
        label: "Events Indexed",
        value: total,
        icon: Layers,
        description: "Historical cards catalogued in UFC lore",
      },
      {
        label: "Countries Logged",
        value: countrySet.size,
        icon: MapPin,
        description: "Global arenas represented on the map",
      },
      {
        label: "Cards This Month",
        value: monthlyUpcoming,
        icon: CalendarDays,
        description: "Scheduled shows inside the current month",
      },
      {
        label: "Filter Presets",
        value: 4,
        icon: Target,
        description: "Quick blends for rivalries, rematches, and tours",
      },
    ];
  }, [filterOptions.locations, total, upcomingEvents]);

  const quickCities = useMemo(() => filterOptions.locations.slice(0, 5), [filterOptions.locations]);
  const quickYears = useMemo(() => filterOptions.years.slice(0, 5), [filterOptions.years]);

  const heroCountdown = useMemo(() => {
    if (!heroEvent) return null;
    return formatDistanceStrict(new Date(heroEvent.date), new Date(), { addSuffix: true });
  }, [heroEvent]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading events...</div>
      </div>
    );
  }

  const hasActiveFilters =
    Boolean(searchQuery) ||
    selectedYears.length > 0 ||
    selectedLocations.length > 0 ||
    selectedEventTypes.length > 0;
  const showPagination = statusFilter !== "upcoming" && total > EVENTS_PER_PAGE && !hasActiveFilters;

  return (
    <div className="relative mx-auto max-w-7xl px-4 pb-16">
      <div className="relative mt-8 overflow-hidden rounded-[3rem] border border-white/10 bg-slate-950/80 shadow-[0_60px_140px_rgba(15,23,42,0.55)] backdrop-blur-xl">
        <div className="absolute inset-0" style={{
          backgroundImage:
            "radial-gradient(circle at 20% 20%, rgba(59,130,246,0.28), transparent 55%), radial-gradient(circle at 80% 30%, rgba(236,72,153,0.25), transparent 60%), linear-gradient(135deg, rgba(15,23,42,0.85) 0%, rgba(2,6,23,0.65) 100%)",
        }} aria-hidden />
        <div className="absolute -top-32 -left-32 h-64 w-64 rounded-full bg-emerald-500/10 blur-3xl" aria-hidden />
        <div className="absolute -bottom-24 right-0 h-80 w-80 rounded-full bg-sky-500/10 blur-3xl" aria-hidden />

        <div className="relative grid gap-10 p-8 sm:p-12 lg:grid-cols-[1.3fr,1fr] lg:items-center">
          <div className="space-y-8 text-white">
            <div className="inline-flex items-center gap-3 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-xs uppercase tracking-[0.35em] text-slate-100">
              <Sparkles className="h-4 w-4" aria-hidden /> UFC Events Hub
            </div>

            <div className="space-y-4">
              <h1 className="text-3xl font-semibold leading-tight sm:text-4xl lg:text-5xl">
                Step into the octagon of history
              </h1>
              <p className="max-w-2xl text-base text-slate-200/80">
                Explore every UFC chapter—track upcoming Pay-Per-Views, relive legendary nights, and craft your own viewing itinerary with cinematic data visualization.
              </p>
            </div>

            {heroEvent && (
              <div className="relative overflow-hidden rounded-2xl border border-white/15 bg-white/5 p-6 shadow-xl shadow-black/30">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.15),transparent_65%)]" aria-hidden />
                <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-300">Next headline</p>
                    <h2 className="text-2xl font-semibold text-white">{heroEvent.name}</h2>
                    <p className="text-sm text-slate-300">
                      {format(parseISO(heroEvent.date), "EEEE, MMMM d yyyy")} · {heroCountdown}
                    </p>
                  </div>
                  <div className="flex flex-col gap-2 text-sm text-slate-200">
                    {heroEvent.location && (
                      <span className="inline-flex items-center gap-2">
                        <MapPin className="h-4 w-4" aria-hidden />
                        {heroEvent.location}
                      </span>
                    )}
                    {heroEvent.broadcast && (
                      <span className="inline-flex items-center gap-2">
                        <LineChart className="h-4 w-4" aria-hidden />
                        {heroEvent.broadcast}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {heroStats.map((stat) => (
              <div
                key={stat.label}
                className="relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-5 text-white shadow-lg shadow-black/20"
              >
                <stat.icon className="mb-4 h-5 w-5 text-sky-300" aria-hidden />
                <p className="text-3xl font-semibold">{stat.value}</p>
                <p className="text-xs uppercase tracking-[0.25em] text-slate-300">{stat.label}</p>
                <p className="mt-3 text-xs text-slate-200/80">{stat.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="sticky top-6 z-40 mt-8">
        <div className="flex flex-col gap-6 rounded-[2.5rem] border border-white/10 bg-slate-950/90 p-6 shadow-2xl shadow-black/40 backdrop-blur-xl">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center">
            <div className="flex flex-1 items-center gap-3">
              <div className="h-12 w-12 shrink-0 rounded-2xl bg-gradient-to-br from-sky-500/30 via-indigo-500/20 to-fuchsia-500/30 p-[1px]">
                <div className="flex h-full w-full items-center justify-center rounded-[1.6rem] bg-slate-950/80">
                  <ListFilter className="h-5 w-5 text-sky-300" aria-hidden />
                </div>
              </div>
              <div className="w-full">
                <EventSearch
                  value={searchQuery}
                  onChange={handleSearchChange}
                  placeholder="Search fighters, venues, rivalries..."
                />
              </div>
            </div>

            <div className="flex items-center gap-2 self-end rounded-full border border-white/10 bg-white/5 p-1 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 lg:self-auto">
              {(
                [
                  { value: "all", label: "All", icon: Layers },
                  { value: "upcoming", label: "Upcoming", icon: Sparkles },
                  { value: "completed", label: "Archive", icon: History },
                ] as const
              ).map((option) => {
                const Icon = option.icon;
                const isActive = statusFilter === option.value;
                return (
                  <button
                    key={option.value}
                    onClick={() => handleFilterChange(option.value)}
                    className={`flex items-center gap-2 rounded-full px-4 py-2 transition-all ${
                      isActive
                        ? "bg-sky-500/20 text-white shadow-[0_0_18px_rgba(56,189,248,0.45)]"
                        : "text-slate-300 hover:text-white"
                    }`}
                  >
                    <Icon className="h-4 w-4" aria-hidden />
                    {option.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs uppercase tracking-[0.25em] text-slate-400">Quick chips</span>
              {quickYears.map((year) => (
                <button
                  key={`quick-year-${year}`}
                  onClick={() => handleYearsChange(selectedYears.includes(year) ? selectedYears.filter((item) => item !== year) : [...selectedYears, year])}
                  className={`rounded-full px-3 py-1 text-xs font-semibold transition-all ${
                    selectedYears.includes(year)
                      ? "bg-sky-500/20 text-sky-100"
                      : "bg-white/5 text-slate-200 hover:bg-white/10"
                  }`}
                >
                  {year}
                </button>
              ))}
              {quickCities.map((city) => (
                <button
                  key={`quick-city-${city}`}
                  onClick={() =>
                    handleLocationsChange(
                      selectedLocations.includes(city)
                        ? selectedLocations.filter((item) => item !== city)
                        : [...selectedLocations, city]
                    )
                  }
                  className={`rounded-full px-3 py-1 text-xs font-semibold transition-all ${
                    selectedLocations.includes(city)
                      ? "bg-emerald-500/20 text-emerald-100"
                      : "bg-white/5 text-slate-200 hover:bg-white/10"
                  }`}
                >
                  {city}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 p-1 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200">
                <button
                  onClick={() => setViewMode("grid")}
                  className={`flex items-center gap-2 rounded-full px-4 py-2 transition-all ${
                    viewMode === "grid"
                      ? "bg-white/15 text-white shadow-[0_0_18px_rgba(148,163,184,0.4)]"
                      : "text-slate-300 hover:text-white"
                  }`}
                >
                  <Rows2 className="h-4 w-4" aria-hidden />
                  Grid
                </button>
                <button
                  onClick={() => setViewMode("timeline")}
                  className={`flex items-center gap-2 rounded-full px-4 py-2 transition-all ${
                    viewMode === "timeline"
                      ? "bg-white/15 text-white shadow-[0_0_18px_rgba(148,163,184,0.4)]"
                      : "text-slate-300 hover:text-white"
                  }`}
                >
                  <Circle className="h-4 w-4" aria-hidden />
                  Timeline
                </button>
              </div>

              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] transition-all ${
                  showFilters || hasActiveFilters
                    ? "border-sky-400/60 bg-sky-500/10 text-sky-100"
                    : "border-white/10 bg-white/5 text-slate-200 hover:border-slate-400/40"
                }`}
              >
                <Filter className="h-4 w-4" aria-hidden /> Filters
              </button>
            </div>
          </div>

          {hasActiveFilters && (
            <div className="flex flex-wrap gap-2">
              {searchQuery && (
                <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs text-slate-200">
                  Search: {searchQuery}
                </span>
              )}
              {selectedYears.map((year) => (
                <span
                  key={`chip-year-${year}`}
                  className="inline-flex items-center gap-2 rounded-full border border-sky-400/40 bg-sky-500/10 px-3 py-1 text-xs text-sky-100"
                >
                  {year}
                  <button
                    onClick={() => handleYearsChange(selectedYears.filter((item) => item !== year))}
                    className="rounded-full border border-transparent p-1 hover:border-sky-200/60"
                    aria-label={`Remove year ${year}`}
                  >
                    ×
                  </button>
                </span>
              ))}
              {selectedLocations.map((location) => (
                <span
                  key={`chip-location-${location}`}
                  className="inline-flex items-center gap-2 rounded-full border border-emerald-400/40 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-100"
                >
                  {location}
                  <button
                    onClick={() =>
                      handleLocationsChange(selectedLocations.filter((item) => item !== location))
                    }
                    className="rounded-full border border-transparent p-1 hover:border-emerald-200/60"
                    aria-label={`Remove location ${location}`}
                  >
                    ×
                  </button>
                </span>
              ))}
              {selectedEventTypes.map((eventType) => (
                <span
                  key={`chip-type-${eventType}`}
                  className="inline-flex items-center gap-2 rounded-full border border-purple-400/40 bg-purple-500/10 px-3 py-1 text-xs text-purple-100"
                >
                  {EVENT_TYPE_CONFIGS[eventType]?.label ?? eventType}
                  <button
                    onClick={() =>
                      handleEventTypesChange(
                        selectedEventTypes.filter((item) => item !== eventType)
                      )
                    }
                    className="rounded-full border border-transparent p-1 hover:border-purple-200/60"
                    aria-label={`Remove ${eventType} filter`}
                  >
                    ×
                  </button>
                </span>
              ))}
              <button
                onClick={handleClearAllFilters}
                className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-200 hover:border-white/30"
              >
                Clear all
              </button>
            </div>
          )}

          {showFilters && (
            <EventFilters
              years={filterOptions.years}
              locations={filterOptions.locations}
              selectedYears={selectedYears}
              selectedLocations={selectedLocations}
              selectedEventTypes={selectedEventTypes}
              onYearsChange={handleYearsChange}
              onLocationsChange={handleLocationsChange}
              onEventTypesChange={handleEventTypesChange}
              onClearAll={handleClearAllFilters}
              onClose={() => setShowFilters(false)}
            />
          )}
        </div>
      </div>

      <div className="mt-10">
        {viewMode === "grid" ? (
          <div className="grid grid-cols-1 gap-6">
            {events.map((event) => (
              <EventCard key={event.event_id} event={event} />
            ))}
          </div>
        ) : (
          <EventTimeline events={events} />
        )}
      </div>

      {/* Pagination */}
      {showPagination && (
        <div className="mt-8 flex items-center justify-center gap-4">
          <button
            onClick={handlePrevPage}
            disabled={offset === 0}
            className="px-4 py-2 bg-gray-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600 transition-colors"
          >
            Previous
          </button>
          <span className="text-gray-400">
            Page {Math.floor(offset / EVENTS_PER_PAGE) + 1} of{" "}
            {Math.ceil(total / EVENTS_PER_PAGE)}
          </span>
          <button
            onClick={handleNextPage}
            disabled={offset + EVENTS_PER_PAGE >= total}
            className="px-4 py-2 bg-gray-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600 transition-colors"
          >
            Next
          </button>
        </div>
      )}

      {events.length === 0 && !loading && (
        <div className="text-center py-12 text-gray-400">
          <p className="text-xl mb-2">No events found.</p>
          {hasActiveFilters && (
            <p className="text-sm">Try adjusting your search or filters.</p>
          )}
        </div>
      )}
    </div>
  );
}
