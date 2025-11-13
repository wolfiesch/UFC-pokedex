"use client";

import { useState, useEffect, useMemo } from "react";
import { isSameMonth, parseISO } from "date-fns";
import {
  ArrowRightCircle,
  CalendarDays,
  Compass,
  Filter,
  LayoutGrid,
  ListTree,
  MapPin,
  Play,
  Sparkles,
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

  // Search and filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null);
  const [selectedEventType, setSelectedEventType] = useState<EventType | null>(null);

  // Filter options from API
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    years: [],
    locations: [],
    event_types: [],
  });

  const [showFilters, setShowFilters] = useState(false);

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
        const hasFilters = searchQuery || selectedYear || selectedLocation || selectedEventType;

        if (hasFilters) {
          // Use search endpoint with filters
          url = `/api/events/search/`;
          if (searchQuery) params.set("q", searchQuery);
          if (selectedYear) params.set("year", selectedYear.toString());
          if (selectedLocation) params.set("location", selectedLocation);
          if (selectedEventType) params.set("event_type", selectedEventType);
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
  }, [offset, statusFilter, searchQuery, selectedYear, selectedLocation, selectedEventType]);

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

  const handleYearChange = (year: number | null) => {
    setSelectedYear(year);
    setOffset(0);
  };

  const handleLocationChange = (location: string | null) => {
    setSelectedLocation(location);
    setOffset(0);
  };

  const handleEventTypeChange = (eventType: EventType | null) => {
    setSelectedEventType(eventType);
    setOffset(0);
  };

  const heroHighlight = useMemo(() => {
    if (events.length === 0) {
      return null;
    }

    const upcomingEvents = events.filter((eventItem) => eventItem.status === "upcoming");
    const prioritized =
      upcomingEvents.find((eventItem) => {
        const eventType =
          normalizeEventType(eventItem.event_type ?? null) ?? detectEventType(eventItem.name);
        return eventType === "ppv";
      }) ?? upcomingEvents.at(0) ?? events.at(0);

    if (!prioritized) {
      return null;
    }

    const resolvedType =
      normalizeEventType(prioritized.event_type ?? null) ?? detectEventType(prioritized.name);
    const typeConfig = getEventTypeConfig(resolvedType);

    return {
      event: prioritized,
      typeConfig,
    };
  }, [events]);

  const statistics = useMemo(() => {
    if (events.length === 0) {
      return {
        upcomingThisMonth: 0,
        uniqueCountries: 0,
        indexedEvents: total,
      };
    }

    const now = new Date();
    const upcomingThisMonth = events.filter((eventItem) => {
      const eventDate = parseISO(eventItem.date);
      return isSameMonth(eventDate, now) && eventDate >= now;
    }).length;

    const countries = new Set<string>();
    events.forEach((eventItem) => {
      if (!eventItem.location) {
        return;
      }
      const segments = eventItem.location.split(",");
      const country = segments.at(-1)?.trim();
      if (country) {
        countries.add(country);
      }
    });

    return {
      upcomingThisMonth,
      uniqueCountries: countries.size,
      indexedEvents: total,
    };
  }, [events, total]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200">
        <div className="flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-6 py-3 text-sm uppercase tracking-[0.4em]">
          <Play className="h-4 w-4 animate-pulse" aria-hidden="true" />
          Loading cards…
        </div>
      </div>
    );
  }

  const hasActiveFilters = Boolean(searchQuery || selectedYear || selectedLocation || selectedEventType);
  const showPagination = statusFilter !== "upcoming" && total > EVENTS_PER_PAGE && !hasActiveFilters;

  return (
    <div className="relative mx-auto flex max-w-6xl flex-col gap-12 px-4 pb-16 pt-10 sm:px-6 lg:px-8">
      <section className="relative overflow-hidden rounded-[40px] border border-white/10 bg-slate-950 shadow-[0_60px_120px_-70px_rgba(15,23,42,0.9)]">
        <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1579974640221-d1bd61b0843b?auto=format&fit=crop&w=1600&q=80')] bg-cover bg-center opacity-60" />
        <div className="absolute inset-0 bg-gradient-to-br from-black via-slate-950/70 to-slate-950" />
        <div className="relative z-10 grid gap-10 px-8 pb-16 pt-14 md:grid-cols-[1.2fr_0.8fr] md:px-14 md:pb-20 md:pt-16">
          <div className="space-y-6 text-slate-100">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1 text-xs font-semibold uppercase tracking-[0.35em]">
              <Sparkles className="h-4 w-4" aria-hidden="true" />
              UFC Events Atlas
            </span>
            <h1 className="text-4xl font-extrabold tracking-tight drop-shadow-md md:text-5xl">
              Step into the octagon’s living history.
            </h1>
            <p className="max-w-xl text-base text-slate-200/80">
              Explore every card we’ve indexed, chart global venues, and follow the momentum of upcoming fights. Search, filter,
              and timeline-hop without breaking flow—the experience is crafted as a cinematic control room for fight fans.
            </p>

            <dl className="grid gap-4 text-sm sm:grid-cols-3">
              <div className="rounded-3xl border border-white/10 bg-white/5 p-4">
                <dt className="flex items-center gap-2 text-xs uppercase tracking-[0.35em] text-slate-200/70">
                  <LayoutGrid className="h-4 w-4" aria-hidden="true" /> Indexed
                </dt>
                <dd className="mt-2 text-2xl font-bold text-white">{statistics.indexedEvents.toLocaleString()}</dd>
              </div>
              <div className="rounded-3xl border border-white/10 bg-white/5 p-4">
                <dt className="flex items-center gap-2 text-xs uppercase tracking-[0.35em] text-slate-200/70">
                  <Compass className="h-4 w-4" aria-hidden="true" /> Countries
                </dt>
                <dd className="mt-2 text-2xl font-bold text-white">{statistics.uniqueCountries}</dd>
              </div>
              <div className="rounded-3xl border border-white/10 bg-white/5 p-4">
                <dt className="flex items-center gap-2 text-xs uppercase tracking-[0.35em] text-slate-200/70">
                  <CalendarDays className="h-4 w-4" aria-hidden="true" /> This Month
                </dt>
                <dd className="mt-2 text-2xl font-bold text-white">{statistics.upcomingThisMonth}</dd>
              </div>
            </dl>
          </div>

          <div className="relative flex h-full flex-col justify-between rounded-[30px] border border-white/20 bg-white/10 p-6 backdrop-blur">
            {heroHighlight && (
              <div className="space-y-4">
                <p className="text-xs font-semibold uppercase tracking-[0.35em] text-slate-200/70">Next Spotlight</p>
                <h2 className="text-2xl font-bold text-white">{heroHighlight.event.name}</h2>
                <div className="flex flex-wrap items-center gap-2 text-sm text-slate-100/90">
                  <CalendarDays className="h-4 w-4 text-cyan-300" aria-hidden="true" />
                  <span>{formatEventDate(heroHighlight.event.date)}</span>
                </div>
                {heroHighlight.event.location && (
                  <div className="flex flex-wrap items-center gap-2 text-sm text-slate-100/90">
                    <MapPin className="h-4 w-4 text-rose-300" aria-hidden="true" />
                    <span>{heroHighlight.event.location}</span>
                  </div>
                )}
                <div className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-semibold">
                  <span>{heroHighlight.typeConfig.label}</span>
                  <ArrowRightCircle className="h-4 w-4" aria-hidden="true" />
                  In Focus
                </div>
              </div>
            )}
            <p className="text-xs text-slate-300/70">
              Scroll to activate the events console below—filters stay docked so you can remix storylines and build watchlists without losing your place.
            </p>
          </div>
        </div>
      </section>

      <div className="sticky top-16 z-30 -mt-24 space-y-6 rounded-[30px] border border-white/10 bg-slate-900/80 p-6 shadow-[0_35px_80px_-55px_rgba(15,23,42,0.95)] backdrop-blur">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <EventSearch
            value={searchQuery}
            onChange={handleSearchChange}
            placeholder="Search by city, headliner, or event tag"
            className="bg-gradient-to-r from-white/10 via-white/5 to-transparent"
          />
          <div className="flex flex-wrap items-center gap-3 text-xs uppercase tracking-[0.3em] text-slate-200/70">
            <Filter className="h-4 w-4" aria-hidden="true" />
            <span>Dynamic Dashboard Controls</span>
          </div>
        </div>

        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            {(
              [
                { key: "all" as const, label: `All Events (${total})` },
                { key: "upcoming" as const, label: "Upcoming" },
                { key: "completed" as const, label: "Completed" },
              ]
            ).map((segment) => (
              <button
                key={segment.key}
                type="button"
                onClick={() => handleFilterChange(segment.key)}
                className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.25em] transition ${
                  statusFilter === segment.key
                    ? "border-cyan-400/80 bg-cyan-400/20 text-cyan-100 shadow-[0_0_25px_rgba(34,211,238,0.35)]"
                    : "border-white/10 bg-white/5 text-slate-200 hover:border-white/25 hover:bg-white/10"
                }`}
              >
                <Sparkles className="h-4 w-4" aria-hidden="true" />
                {segment.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 p-1 text-xs font-semibold uppercase tracking-[0.35em] text-slate-200">
            <button
              type="button"
              onClick={() => setViewMode("grid")}
              className={`flex items-center gap-2 rounded-full px-3 py-1.5 transition ${
                viewMode === "grid" ? "bg-white/15 text-white" : "hover:bg-white/10"
              }`}
            >
              <LayoutGrid className="h-4 w-4" aria-hidden="true" /> Grid
            </button>
            <button
              type="button"
              onClick={() => setViewMode("timeline")}
              className={`flex items-center gap-2 rounded-full px-3 py-1.5 transition ${
                viewMode === "timeline" ? "bg-white/15 text-white" : "hover:bg-white/10"
              }`}
            >
              <ListTree className="h-4 w-4" aria-hidden="true" /> Timeline
            </button>
          </div>
        </div>

        <EventFilters
          years={filterOptions.years}
          locations={filterOptions.locations}
          selectedYear={selectedYear}
          selectedLocation={selectedLocation}
          selectedEventType={selectedEventType}
          onYearChange={handleYearChange}
          onLocationChange={handleLocationChange}
          onEventTypeChange={handleEventTypeChange}
        />
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

      {showPagination && (
        <div className="flex items-center justify-center gap-6 text-sm text-slate-100">
          <button
            onClick={handlePrevPage}
            disabled={offset === 0}
            className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-5 py-2 font-semibold uppercase tracking-[0.25em] text-slate-100 transition disabled:cursor-not-allowed disabled:opacity-40 hover:border-white/40 hover:bg-white/10"
          >
            ← Previous
          </button>
          <span className="text-xs uppercase tracking-[0.35em] text-slate-300/80">
            Page {Math.floor(offset / EVENTS_PER_PAGE) + 1} of {Math.ceil(total / EVENTS_PER_PAGE)}
          </span>
          <button
            onClick={handleNextPage}
            disabled={offset + EVENTS_PER_PAGE >= total}
            className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-5 py-2 font-semibold uppercase tracking-[0.25em] text-slate-100 transition disabled:cursor-not-allowed disabled:opacity-40 hover:border-white/40 hover:bg-white/10"
          >
            Next →
          </button>
        </div>
      )}

      {events.length === 0 && !loading && (
        <div className="rounded-3xl border border-white/10 bg-white/5 py-20 text-center text-slate-200">
          <p className="text-2xl font-semibold uppercase tracking-[0.4em]">No events found</p>
          {hasActiveFilters ? (
            <p className="mt-2 text-sm text-slate-300/80">Refresh your filters or try a different search query.</p>
          ) : (
            <p className="mt-2 text-sm text-slate-300/80">We could not surface events at this time.</p>
          )}
        </div>
      )}
    </div>
  );
}

function formatEventDate(date: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(parseISO(date));
}
