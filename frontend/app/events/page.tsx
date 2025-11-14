"use client";

import { useEffect, useMemo, useState } from "react";
import {
  differenceInDays,
  differenceInHours,
  differenceInMinutes,
  format,
  isAfter,
  isSameMonth,
  parseISO,
} from "date-fns";
import {
  detectEventType,
  normalizeEventType,
  type EventType,
} from "@/lib/event-utils";
import EventCard from "@/components/events/EventCard";
import EventTimeline from "@/components/events/EventTimeline";
import EventFilters, {
  type SavedFilterPreset,
} from "@/components/events/EventFilters";
import {
  CalendarDays,
  Clock,
  Flame,
  GaugeCircle,
  Globe2,
  LucideIcon,
  MapPin,
  Sparkles,
  Target,
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

  const [upcomingEvents, setUpcomingEvents] = useState<Event[]>([]);

  // Persisted filter presets that we can hydrate into the toolbar
  const filterPresets: SavedFilterPreset[] = useMemo(() => {
    const currentYear = new Date().getFullYear();

    return [
      {
        id: "ppv-spotlight",
        name: "PPV Spotlight",
        description: "Pay-per-view blockbusters this year",
        filters: {
          years: [currentYear],
          locations: [],
          eventTypes: ["ppv"],
          status: "upcoming",
        },
      },
      {
        id: "fight-night-tour",
        name: "Fight Night Tour",
        description: "Traveling Fight Night cards worldwide",
        filters: {
          years: [],
          locations: [],
          eventTypes: ["fight_night"],
          status: "all",
        },
      },
      {
        id: "vegas-legends",
        name: "Vegas Legends",
        description: "Recent events on the Strip",
        filters: {
          years: [currentYear - 1, currentYear],
          locations: ["Las Vegas"],
          eventTypes: [],
          status: "all",
        },
      },
    ];
  }, []);

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
        const hasFilterInput =
          searchQuery ||
          selectedYears.length > 0 ||
          selectedLocations.length > 0 ||
          selectedEventTypes.length > 0;
        const multiSelectActive =
          selectedYears.length > 1 ||
          selectedLocations.length > 1 ||
          selectedEventTypes.length > 1 ||
          [selectedYears.length, selectedLocations.length, selectedEventTypes.length].filter(
            (value) => value > 0,
          ).length > 1;

        const buildSearchParams = (
          year: number | null,
          location: string | null,
          eventType: EventType | null,
        ) => {
          const searchParams = new URLSearchParams();
          if (searchQuery) searchParams.set("q", searchQuery);
          if (year) searchParams.set("year", year.toString());
          if (location) searchParams.set("location", location);
          if (eventType) searchParams.set("event_type", eventType);
          if (statusFilter !== "all") searchParams.set("status", statusFilter);
          searchParams.set("limit", EVENTS_PER_PAGE.toString());
          return searchParams;
        };

        if (hasFilterInput && multiSelectActive) {
          const yearOptions = selectedYears.length > 0 ? selectedYears : [null];
          const locationOptions = selectedLocations.length > 0 ? selectedLocations : [null];
          const typeOptions = selectedEventTypes.length > 0 ? selectedEventTypes : [null];

          const requests = yearOptions.flatMap((yearOption) =>
            locationOptions.flatMap((locationOption) =>
              typeOptions.map(async (typeOption) => {
                const searchParams = buildSearchParams(
                  yearOption,
                  locationOption,
                  typeOption,
                );

                const response = await fetch(
                  `/api/events/search/?${searchParams.toString()}`,
                  { cache: "no-store" },
                );

                if (!response.ok) {
                  throw new Error(
                    `Failed to fetch combined filters: ${response.statusText}`,
                  );
                }

                return response.json();
              }),
            ),
          );

          const payloads = await Promise.all(requests);

          const aggregated = payloads
            .flatMap((payload) => (Array.isArray(payload) ? payload : payload.events || []))
            .reduce((accumulator, item) => {
              if (!accumulator.some((existing) => existing.event_id === item.event_id)) {
                accumulator.push(item);
              }
              return accumulator;
            }, [] as Event[])
            .sort((a, b) => parseISO(b.date).getTime() - parseISO(a.date).getTime());

          setEvents(aggregated);
          setTotal(aggregated.length);
          return;
        }

        if (hasFilterInput) {
          url = `/api/events/search/`;
          const year = selectedYears[0] ?? null;
          const location = selectedLocations[0] ?? null;
          const eventType = selectedEventTypes[0] ?? null;
          const searchParams = buildSearchParams(year, location, eventType);
          url = `${url}?${searchParams.toString()}`;
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

        if (Array.isArray(data)) {
          setEvents(data);
          setTotal(data.length);
        } else {
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
    async function hydrateUpcomingEvents() {
      try {
        const response = await fetch(`/api/events/upcoming`, { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`Failed to hydrate upcoming events: ${response.statusText}`);
        }

        const data: Event[] = await response.json();
        setUpcomingEvents(data);
      } catch (error) {
        console.error("Error fetching upcoming overview:", error);
      }
    }

    hydrateUpcomingEvents();
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
    setOffset(0);
  };

  const handleSearchChange = (query: string) => {
    setSearchQuery(query);
    setOffset(0);
  };

  const toggleYear = (year: number) => {
    setSelectedYears((previous) => {
      const exists = previous.includes(year);
      const next = exists ? previous.filter((value) => value !== year) : [...previous, year];
      return [...next].sort((a, b) => b - a);
    });
    setOffset(0);
  };

  const toggleLocation = (location: string) => {
    setSelectedLocations((previous) => {
      const exists = previous.includes(location);
      const next = exists
        ? previous.filter((value) => value !== location)
        : [...previous, location];
      return next;
    });
    setOffset(0);
  };

  const toggleEventType = (eventType: EventType) => {
    setSelectedEventTypes((previous) => {
      const exists = previous.includes(eventType);
      const next = exists
        ? previous.filter((value) => value !== eventType)
        : [...previous, eventType];
      return next;
    });
    setOffset(0);
  };

  const clearAllFilters = () => {
    setSelectedYears([]);
    setSelectedLocations([]);
    setSelectedEventTypes([]);
    setSearchQuery("");
    setStatusFilter("all");
    setOffset(0);
  };

  const applyPreset = (preset: SavedFilterPreset) => {
    setSelectedYears(preset.filters.years);
    setSelectedLocations(preset.filters.locations);
    setSelectedEventTypes(preset.filters.eventTypes);
    if (preset.filters.status) {
      setStatusFilter(preset.filters.status);
    }
    setOffset(0);
  };

  const removeFilterChip = (type: "year" | "location" | "eventType", value: string | number) => {
    if (type === "year" && typeof value === "number") {
      toggleYear(value);
    }

    if (type === "location" && typeof value === "string") {
      toggleLocation(value);
    }

    if (type === "eventType" && typeof value === "string") {
      toggleEventType(value as EventType);
    }
  };

  const popularYears = useMemo(() => {
    return filterOptions.years.slice(0, 4);
  }, [filterOptions.years]);

  const popularCities = useMemo(() => {
    return filterOptions.locations.slice(0, 6);
  }, [filterOptions.locations]);

  const uniqueCountryCount = useMemo(() => {
    const countries = new Set<string>();
    filterOptions.locations.forEach((location) => {
      const parts = location.split(",");
      const candidate = parts[parts.length - 1]?.trim();
      if (candidate) {
        countries.add(candidate);
      }
    });

    return countries.size;
  }, [filterOptions.locations]);

  const upcomingThisMonth = useMemo(() => {
    if (upcomingEvents.length === 0) {
      return 0;
    }

    const now = new Date();
    return upcomingEvents.filter((event) => {
      const eventDate = parseISO(event.date);
      return isAfter(eventDate, now) && isSameMonth(eventDate, now);
    }).length;
  }, [upcomingEvents]);

  const nextPpvEvent = useMemo(() => {
    if (upcomingEvents.length === 0) {
      return null;
    }

    const sorted = [...upcomingEvents].sort(
      (a, b) => parseISO(a.date).getTime() - parseISO(b.date).getTime(),
    );

    const ppvCandidate = sorted.find((event) => {
      const normalized = normalizeEventType(event.event_type ?? null);
      const detected = normalized ?? detectEventType(event.name);
      return detected === "ppv";
    });

    return ppvCandidate ?? sorted[0];
  }, [upcomingEvents]);

  const heroAccentByType: Record<EventType, string> = {
    ppv: "from-amber-500/40 via-amber-400/20 to-amber-600/30",
    fight_night: "from-rose-500/40 via-red-500/25 to-rose-600/30",
    ufc_on_espn: "from-red-500/35 via-orange-500/25 to-yellow-500/30",
    ufc_on_abc: "from-blue-500/40 via-sky-400/25 to-cyan-400/30",
    tuf_finale: "from-purple-500/35 via-fuchsia-400/25 to-purple-600/30",
    contender_series: "from-emerald-500/35 via-teal-400/25 to-emerald-600/30",
    other: "from-slate-700/40 via-slate-600/25 to-slate-800/30",
  };

  const nextPpvAccent = nextPpvEvent
    ? heroAccentByType[
        normalizeEventType(nextPpvEvent.event_type ?? null) ?? detectEventType(nextPpvEvent.name)
      ]
    : "from-slate-800 to-slate-900";

  const countdownLabel = useMemo(() => {
    if (!nextPpvEvent) {
      return "Awaiting schedule";
    }

    const eventDate = parseISO(nextPpvEvent.date);
    const now = new Date();

    if (!isAfter(eventDate, now)) {
      return "Already underway";
    }

    const days = differenceInDays(eventDate, now);
    const hours = differenceInHours(eventDate, now) - days * 24;
    const minutes = Math.max(
      differenceInMinutes(eventDate, now) - differenceInHours(eventDate, now) * 60,
      0,
    );

    return `${days}d ${hours}h ${minutes}m`;
  }, [nextPpvEvent]);

  const headlinerLabel = useMemo(() => {
    if (!nextPpvEvent) {
      return "Upcoming card to be announced";
    }

    const parts = nextPpvEvent.name.split(":");
    if (parts.length > 1) {
      return parts.slice(1).join(":").trim();
    }

    const vsIndex = nextPpvEvent.name.toLowerCase().indexOf("vs");
    if (vsIndex > -1) {
      return nextPpvEvent.name.substring(vsIndex).replace(/-/g, " ").trim();
    }

    return nextPpvEvent.name;
  }, [nextPpvEvent]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading events...</div>
      </div>
    );
  }

  const hasActiveFilters =
    searchQuery.length > 0 ||
    selectedYears.length > 0 ||
    selectedLocations.length > 0 ||
    selectedEventTypes.length > 0;

  const multiSelectActive =
    selectedYears.length > 1 ||
    selectedLocations.length > 1 ||
    selectedEventTypes.length > 1 ||
    [selectedYears.length, selectedLocations.length, selectedEventTypes.length].filter(
      (value) => value > 0,
    ).length > 1;

  const showPagination =
    statusFilter !== "upcoming" &&
    total > EVENTS_PER_PAGE &&
    !hasActiveFilters &&
    !multiSelectActive;

  const heroStatCards: Array<{
    id: string;
    label: string;
    value: string;
    icon: LucideIcon;
    description: string;
  }> = [
    {
      id: "indexed",
      label: "Events Indexed",
      value: total.toLocaleString(),
      icon: GaugeCircle,
      description: "Historical cards catalogued across eras",
    },
    {
      id: "countries",
      label: "Countries Represented",
      value: uniqueCountryCount.toString(),
      icon: Globe2,
      description: "Venues spanning the global octagon map",
    },
    {
      id: "this-month",
      label: "Cards This Month",
      value: upcomingThisMonth.toString(),
      icon: Flame,
      description: "Fight nights and PPVs set for this month",
    },
  ];

  return (
    <div className="relative isolate min-h-screen bg-slate-950 pb-16 text-white">
      <div className="pointer-events-none absolute inset-0 opacity-30">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(245,158,11,0.25),transparent_55%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom,rgba(59,130,246,0.15),transparent_60%)]" />
      </div>

      <section className="relative z-10 mx-auto flex w-full max-w-7xl flex-col gap-10 px-4 pb-12 pt-12 sm:px-6 lg:px-8">
        <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-900/60 shadow-[0_20px_60px_rgba(0,0,0,0.45)] backdrop-blur-xl">
          <div className="absolute inset-0">
            <div
              className="absolute inset-0 bg-[url('/textures/octagon-grid.svg')] opacity-40"
              style={{ animation: "hero-pan 36s linear infinite" }}
            />
            <div className="absolute inset-0 bg-gradient-to-br from-black via-slate-950/80 to-slate-900/60" />
            <div className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-gradient-to-b from-transparent via-white/10 to-transparent" />
          </div>

          <div className="relative z-10 grid gap-10 px-6 py-12 lg:grid-cols-5 lg:px-12">
            <div className="lg:col-span-3">
              <div className="mb-8 flex items-center gap-3">
                <span className="rounded-full border border-white/20 bg-white/10 px-4 py-1 text-sm font-semibold tracking-[0.2em] uppercase text-white/80 shadow-inner">
                  UFC Events Command Center
                </span>
              </div>

              <h1 className="text-4xl font-black tracking-tight text-white sm:text-5xl">Step into the Octagon Almanac</h1>
              <p className="mt-4 max-w-xl text-base text-slate-300 sm:text-lg">
                Dive into every UFC event past and present, with immersive storytelling, curated filters, and cinematic previews that bring each fight night to life.
              </p>

              <div className="mt-10 flex flex-col gap-6 rounded-2xl border border-white/10 bg-white/5 p-6 shadow-inner backdrop-blur">
                <div className="flex items-center gap-3">
                  <div
                    className={`flex h-12 w-12 items-center justify-center rounded-xl border border-white/10 bg-gradient-to-br ${nextPpvAccent}`}
                  >
                    <Sparkles className="h-6 w-6 text-amber-200" />
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-widest text-white/60">Next up</p>
                    <p className="text-lg font-semibold text-white">
                      {nextPpvEvent ? nextPpvEvent.name : "Awaiting announcement"}
                    </p>
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                    <div className="flex items-center gap-3">
                      <CalendarDays className="h-5 w-5 text-white/70" />
                      <div>
                        <p className="text-xs uppercase tracking-wide text-white/50">Date</p>
                        <p className="font-semibold text-white">
                          {nextPpvEvent ? format(parseISO(nextPpvEvent.date), "MMMM d, yyyy") : "TBA"}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                    <div className="flex items-center gap-3">
                      <Clock className="h-5 w-5 text-white/70" />
                      <div>
                        <p className="text-xs uppercase tracking-wide text-white/50">Countdown</p>
                        <p className="font-semibold text-white">{countdownLabel}</p>
                      </div>
                    </div>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                    <div className="flex items-center gap-3">
                      <Target className="h-5 w-5 text-white/70" />
                      <div>
                        <p className="text-xs uppercase tracking-wide text-white/50">Headliners</p>
                        <p className="font-semibold text-white">{headlinerLabel}</p>
                      </div>
                    </div>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                    <div className="flex items-center gap-3">
                      <MapPin className="h-5 w-5 text-white/70" />
                      <div>
                        <p className="text-xs uppercase tracking-wide text-white/50">Location</p>
                        <p className="font-semibold text-white">{nextPpvEvent?.location ?? "To be confirmed"}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="lg:col-span-2">
              <div className="grid gap-4">
                {heroStatCards.map(({ id, label, value, icon: Icon, description }) => (
                  <div
                    key={id}
                    className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-5 shadow-lg backdrop-blur transition hover:border-white/20 hover:bg-white/10"
                  >
                    <div className="absolute inset-0 opacity-0 transition group-hover:opacity-100">
                      <div className="absolute -top-10 right-0 h-24 w-24 rounded-full bg-white/10 blur-2xl" />
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-white/10 to-transparent">
                        <Icon className="h-6 w-6 text-white" />
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-widest text-white/60">{label}</p>
                        <p className="text-2xl font-bold text-white">{value}</p>
                        <p className="mt-1 text-xs text-white/50">{description}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="sticky top-4 z-20">
          <EventFilters
            years={filterOptions.years}
            locations={filterOptions.locations}
            selectedYears={selectedYears}
            selectedLocations={selectedLocations}
            selectedEventTypes={selectedEventTypes}
            statusFilter={statusFilter}
            viewMode={viewMode}
            searchQuery={searchQuery}
            popularYears={popularYears}
            popularLocations={popularCities}
            presets={filterPresets}
            onSearchChange={handleSearchChange}
            onToggleYear={toggleYear}
            onToggleLocation={toggleLocation}
            onToggleEventType={toggleEventType}
            onStatusFilterChange={handleFilterChange}
            onViewModeChange={setViewMode}
            onClearAll={clearAllFilters}
            onApplyPreset={applyPreset}
            onRemoveFilterChip={removeFilterChip}
            hasActiveFilters={hasActiveFilters}
          />
        </div>
      </section>

      <div className="relative z-10 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        {viewMode === "grid" ? (
          <div className="grid grid-cols-1 gap-6 pb-16">
            {events.map((event) => (
              <EventCard key={event.event_id} event={event} />
            ))}
          </div>
        ) : (
          <EventTimeline events={events} />
        )}

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
              Page {Math.floor(offset / EVENTS_PER_PAGE) + 1} of {Math.ceil(total / EVENTS_PER_PAGE)}
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
            {hasActiveFilters && <p className="text-sm">Try adjusting your search or filters.</p>}
          </div>
        )}
      </div>
    </div>
  );
}
