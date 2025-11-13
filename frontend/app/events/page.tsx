"use client";

import { useEffect, useMemo, useState, type SVGProps } from "react";
import { format, formatDistanceToNowStrict, parseISO, startOfMonth, endOfMonth, isWithinInterval } from "date-fns";
import { cn } from "@/lib/utils";
import EventCard from "@/components/events/EventCard";
import EventSearch from "@/components/events/EventSearch";
import EventFilters from "@/components/events/EventFilters";
import EventTimeline from "@/components/events/EventTimeline";
import type { EventType } from "@/lib/event-utils";
import { detectEventType, normalizeEventType } from "@/lib/event-utils";
import {
  Activity,
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  Flame,
  Globe2,
  LayoutGrid,
  ListTimeline,
  LucideIcon,
  MapPin,
  SlidersHorizontal,
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

type HeroStat = {
  label: string;
  value: string;
  helper: string;
  icon: LucideIcon;
};

type HeroEventInsights = {
  countdown: string;
  formattedDate: string;
  headliner?: string;
};

export default function EventsPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [total, setTotal] = useState(0);
  const [catalogTotal, setCatalogTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<"all" | "upcoming" | "completed">("all");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedYears, setSelectedYears] = useState<number[]>([]);
  const [selectedLocations, setSelectedLocations] = useState<string[]>([]);
  const [selectedEventTypes, setSelectedEventTypes] = useState<EventType[]>([]);

  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    years: [],
    locations: [],
    event_types: [],
  });

  const [filtersVisible, setFiltersVisible] = useState(false);
  const [heroUpcoming, setHeroUpcoming] = useState<Event[]>([]);

  useEffect(() => {
    async function fetchFilterOptions() {
      try {
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
    async function fetchHighlights() {
      try {
        const response = await fetch(`/api/events/upcoming`, { cache: "no-store" });
        if (!response.ok) {
          throw new Error(response.statusText);
        }
        const data: Event[] = await response.json();
        setHeroUpcoming(data);
      } catch (error) {
        console.error("Error fetching hero highlights:", error);
      }
    }

    fetchHighlights();
  }, []);

  useEffect(() => {
    async function fetchEvents() {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (offset > 0) params.set("offset", offset.toString());
        params.set("limit", EVENTS_PER_PAGE.toString());

        let url: string;
        const hasFilters =
          Boolean(searchQuery) ||
          selectedYears.length > 0 ||
          selectedLocations.length > 0 ||
          selectedEventTypes.length > 0;

        if (hasFilters) {
          url = `/api/events/search/`;
          if (searchQuery) params.set("q", searchQuery);
          if (selectedYears[0]) params.set("year", selectedYears[0].toString());
          if (selectedLocations[0]) params.set("location", selectedLocations[0]);
          if (selectedEventTypes[0]) params.set("event_type", selectedEventTypes[0]);
          if (statusFilter !== "all") params.set("status", statusFilter);
        } else {
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

        const data: PaginatedEventsResponse | Event[] = await response.json();

        let fetchedEvents: Event[];
        if (Array.isArray(data)) {
          fetchedEvents = data;
          setCatalogTotal(data.length);
        } else {
          fetchedEvents = data.events || [];
          setCatalogTotal(data.total || fetchedEvents.length);
        }

        let filteredEvents = [...fetchedEvents];

        if (selectedYears.length > 0) {
          filteredEvents = filteredEvents.filter((event) => {
            const eventYear = parseISO(event.date).getFullYear();
            return selectedYears.includes(eventYear);
          });
        }

        if (selectedLocations.length > 0) {
          filteredEvents = filteredEvents.filter((event) =>
            event.location ? selectedLocations.some((location) => event.location?.includes(location)) : false
          );
        }

        if (selectedEventTypes.length > 0) {
          filteredEvents = filteredEvents.filter((event) => {
            const normalized = normalizeEventType(event.event_type ?? null) ?? detectEventType(event.name);
            return selectedEventTypes.includes(normalized);
          });
        }

        setEvents(filteredEvents);
        setTotal(filteredEvents.length);
      } catch (error) {
        console.error("Error fetching events:", error);
        setEvents([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    }

    fetchEvents();
  }, [offset, statusFilter, searchQuery, selectedYears, selectedLocations, selectedEventTypes]);

  const handleNextPage = () => {
    if (offset + EVENTS_PER_PAGE < catalogTotal) {
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

  const toggleYear = (year: number) => {
    setSelectedYears((prev) =>
      prev.includes(year) ? prev.filter((value) => value !== year) : [...prev, year]
    );
    setOffset(0);
  };

  const toggleLocation = (location: string) => {
    setSelectedLocations((prev) =>
      prev.includes(location) ? prev.filter((value) => value !== location) : [...prev, location]
    );
    setOffset(0);
  };

  const toggleEventType = (eventType: EventType) => {
    setSelectedEventTypes((prev) =>
      prev.includes(eventType) ? prev.filter((value) => value !== eventType) : [...prev, eventType]
    );
    setOffset(0);
  };

  const handleFilterChange = (newFilter: "all" | "upcoming" | "completed") => {
    setStatusFilter(newFilter);
    setOffset(0);
  };

  const handleSearchChange = (query: string) => {
    setSearchQuery(query);
    setOffset(0);
  };

  const quickYears = useMemo(() => filterOptions.years.slice(-4).reverse(), [filterOptions.years]);
  const quickCities = useMemo(() => filterOptions.locations.slice(0, 6), [filterOptions.locations]);

  const hasActiveFilters =
    Boolean(searchQuery) ||
    selectedYears.length > 0 ||
    selectedLocations.length > 0 ||
    selectedEventTypes.length > 0;

  const showPagination =
    statusFilter !== "upcoming" && !hasActiveFilters && catalogTotal > EVENTS_PER_PAGE;

  const heroEvent = useMemo(() => {
    if (heroUpcoming.length === 0 && events.length === 0) {
      return null;
    }

    const ppvHighlight = heroUpcoming.find((event) => {
      const normalized = normalizeEventType(event.event_type ?? null) ?? detectEventType(event.name);
      return normalized === "ppv";
    });

    return ppvHighlight ?? heroUpcoming[0] ?? events[0] ?? null;
  }, [heroUpcoming, events]);

  const heroInsights: HeroEventInsights | null = useMemo(() => {
    if (!heroEvent) {
      return null;
    }

    const headliner = heroEvent.name.split(":")[1]?.trim();

    return {
      countdown:
        heroEvent.status === "completed"
          ? "Completed"
          : formatDistanceToNowStrict(parseISO(heroEvent.date), { addSuffix: false }),
      formattedDate: format(parseISO(heroEvent.date), "EEEE, MMMM d"),
      headliner,
    };
  }, [heroEvent]);

  const heroStats: HeroStat[] = useMemo(() => {
    const uniqueCountries = new Set<string>();
    filterOptions.locations.forEach((location) => {
      const country = location.split(",").pop()?.trim();
      if (country) uniqueCountries.add(country);
    });

    const upcomingThisMonth = heroUpcoming.filter((event) => {
      if (event.status !== "upcoming") {
        return false;
      }
      const parsed = parseISO(event.date);
      return isWithinInterval(parsed, {
        start: startOfMonth(new Date()),
        end: endOfMonth(new Date()),
      });
    }).length;

    return [
      {
        label: "Events Indexed",
        value: catalogTotal ? catalogTotal.toString() : total.toString(),
        helper: "Across the UFC library",
        icon: Activity,
      },
      {
        label: "Countries",
        value: uniqueCountries.size.toString(),
        helper: "Represented locations",
        icon: Globe2,
      },
      {
        label: "Upcoming this month",
        value: upcomingThisMonth.toString(),
        helper: "Locked-in fight nights & PPVs",
        icon: CalendarDays,
      },
    ];
  }, [catalogTotal, total, filterOptions.locations, heroUpcoming]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading events...</div>
      </div>
    );
  }

  return (
    <div className="relative mx-auto flex max-w-6xl flex-col gap-12 px-4 pb-24">
      <section className="relative -mx-4 overflow-hidden rounded-[40px] border border-white/10 bg-slate-950/80 px-8 pb-16 pt-20 shadow-[0_60px_120px_-80px_rgba(15,23,42,0.95)]">
        <div className="pointer-events-none absolute inset-0 bg-[url('https://images.unsplash.com/photo-1552074284-5e88efcf4c95?auto=format&fit=crop&w=1800&q=80')] bg-cover bg-center opacity-30" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(15,23,42,0.85),_rgba(8,11,20,0.95))]" />

        <div className="relative z-10 grid gap-10 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="flex flex-col gap-6">
            <div className="inline-flex items-center gap-3 self-start rounded-full border border-white/20 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.4em] text-slate-100">
              <Flame className="h-4 w-4 text-amber-300" aria-hidden /> UFC Events Hub
            </div>

            <h1 className="text-balance text-4xl font-black tracking-tight text-white sm:text-5xl">
              Relive every walkout. Track every upcoming card.
            </h1>

            {heroEvent && heroInsights && (
              <div className="space-y-4 rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
                <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Next spotlight</p>
                <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <p className="text-sm font-semibold text-slate-300">{heroInsights.formattedDate}</p>
                    <p className="text-2xl font-black text-white">{heroEvent.name}</p>
                    {heroInsights.headliner && (
                      <p className="text-sm text-slate-200/80">{heroInsights.headliner}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-3 rounded-2xl border border-amber-400/40 bg-amber-500/10 px-4 py-3 text-sm font-semibold text-amber-200">
                    <ClockIcon className="h-5 w-5" aria-hidden />
                    {heroInsights.countdown}
                  </div>
                </div>
                <a
                  href={heroEvent ? `/events/${heroEvent.event_id}` : "#"}
                  className="inline-flex items-center gap-2 text-sm font-semibold text-sky-300 transition hover:text-sky-200"
                >
                  View full card
                  <ArrowUpRight className="h-4 w-4" aria-hidden />
                </a>
              </div>
            )}
          </div>

          <div className="grid gap-4">
            {heroStats.map((stat) => (
              <div
                key={stat.label}
                className="relative overflow-hidden rounded-3xl border border-white/10 bg-white/10 p-6 backdrop-blur transition hover:-translate-y-1 hover:border-white/30"
              >
                <stat.icon className="absolute -top-8 -right-8 h-24 w-24 rotate-12 text-white/10" aria-hidden />
                <p className="text-xs uppercase tracking-[0.3em] text-slate-300">{stat.label}</p>
                <p className="text-3xl font-black text-white">{stat.value}</p>
                <p className="text-xs text-slate-400">{stat.helper}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="sticky top-4 z-40">
        <div className="rounded-[30px] border border-white/10 bg-slate-950/85 p-6 shadow-[0_30px_60px_-40px_rgba(15,23,42,0.9)] backdrop-blur">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="w-full lg:max-w-xl">
              <EventSearch
                value={searchQuery}
                onChange={handleSearchChange}
                placeholder="Search by fighter, venue, or card story..."
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {[
                { key: "all", label: "All", icon: Activity },
                { key: "upcoming", label: "Upcoming", icon: Flame },
                { key: "completed", label: "Completed", icon: CheckCircle2 },
              ].map((item) => (
                <button
                  key={item.key}
                  onClick={() => handleFilterChange(item.key as typeof statusFilter)}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.25em] transition",
                    statusFilter === item.key
                      ? "border-sky-400/60 bg-sky-500/10 text-sky-200"
                      : "border-white/10 bg-white/0 text-slate-300 hover:border-white/30 hover:text-white"
                  )}
                  type="button"
                >
                  <item.icon className="h-4 w-4" aria-hidden />
                  {item.label}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 p-1">
              <button
                onClick={() => setViewMode("grid")}
                className={cn(
                  "flex items-center gap-2 rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] transition",
                  viewMode === "grid"
                    ? "bg-sky-500/10 text-sky-200"
                    : "text-slate-400 hover:text-white"
                )}
                type="button"
              >
                <LayoutGrid className="h-4 w-4" aria-hidden /> Grid
              </button>
              <button
                onClick={() => setViewMode("timeline")}
                className={cn(
                  "flex items-center gap-2 rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] transition",
                  viewMode === "timeline"
                    ? "bg-sky-500/10 text-sky-200"
                    : "text-slate-400 hover:text-white"
                )}
                type="button"
              >
                <ListTimeline className="h-4 w-4" aria-hidden /> Timeline
              </button>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-2">
            {quickYears.map((year) => (
              <button
                key={year}
                onClick={() => toggleYear(year)}
                className={cn(
                  "rounded-full border px-4 py-1 text-xs font-semibold uppercase tracking-[0.25em] transition",
                  selectedYears.includes(year)
                    ? "border-sky-400/60 bg-sky-500/10 text-sky-200"
                    : "border-white/10 bg-white/5 text-slate-300 hover:border-white/30 hover:text-white"
                )}
                type="button"
              >
                {year}
              </button>
            ))}

            {quickCities.map((city) => (
              <button
                key={city}
                onClick={() => toggleLocation(city)}
                className={cn(
                  "rounded-full border px-4 py-1 text-xs font-semibold uppercase tracking-[0.25em] transition",
                  selectedLocations.includes(city)
                    ? "border-emerald-400/60 bg-emerald-500/10 text-emerald-200"
                    : "border-white/10 bg-white/5 text-slate-300 hover:border-white/30 hover:text-white"
                )}
                type="button"
              >
                <MapPin className="mr-2 h-3 w-3" aria-hidden /> {city.split(",")[0]}
              </button>
            ))}
          </div>

          {hasActiveFilters && (
            <div className="mt-6 flex flex-wrap gap-2">
              {selectedYears.map((year) => (
                <button
                  key={`active-year-${year}`}
                  onClick={() => toggleYear(year)}
                  className="inline-flex items-center gap-2 rounded-full border border-sky-400/40 bg-sky-500/10 px-3 py-1 text-xs font-semibold text-sky-100"
                  type="button"
                >
                  {year}
                </button>
              ))}
              {selectedLocations.map((location) => (
                <button
                  key={`active-location-${location}`}
                  onClick={() => toggleLocation(location)}
                  className="inline-flex items-center gap-2 rounded-full border border-emerald-400/40 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-100"
                  type="button"
                >
                  {location}
                </button>
              ))}
              {selectedEventTypes.map((type) => (
                <button
                  key={`active-type-${type}`}
                  onClick={() => toggleEventType(type)}
                  className="inline-flex items-center gap-2 rounded-full border border-amber-400/40 bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-100"
                  type="button"
                >
                  {type.replace(/_/g, " ").toUpperCase()}
                </button>
              ))}
              {searchQuery && (
                <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold text-slate-200">
                  “{searchQuery}”
                </span>
              )}
            </div>
          )}

          <div className="mt-6 flex items-center justify-between">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
              {total} curated stories
            </p>
            <button
              onClick={() => setFiltersVisible((visible) => !visible)}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-slate-200 transition hover:border-white/30 hover:text-white"
              type="button"
            >
              <SlidersHorizontal className="h-4 w-4" aria-hidden /> {filtersVisible ? "Hide" : "Advanced filters"}
            </button>
          </div>

          {filtersVisible && (
            <div className="mt-6">
              <EventFilters
                years={filterOptions.years}
                locations={filterOptions.locations}
                selectedYears={selectedYears}
                selectedLocations={selectedLocations}
                selectedEventTypes={selectedEventTypes}
                onYearsChange={(value) => {
                  setSelectedYears(value);
                  setOffset(0);
                }}
                onLocationsChange={(value) => {
                  setSelectedLocations(value);
                  setOffset(0);
                }}
                onEventTypesChange={(value) => {
                  setSelectedEventTypes(value);
                  setOffset(0);
                }}
              />
            </div>
          )}
        </div>
      </div>

      {viewMode === "grid" ? (
        <div className="grid grid-cols-1 gap-5">
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
            className="px-4 py-2 rounded-full border border-white/10 bg-white/5 text-sm font-semibold text-slate-200 transition hover:border-white/30 disabled:opacity-40 disabled:hover:border-white/10"
            type="button"
          >
            Previous
          </button>
          <span className="text-sm text-slate-400">
            Page {Math.floor(offset / EVENTS_PER_PAGE) + 1} of {Math.ceil(catalogTotal / EVENTS_PER_PAGE)}
          </span>
          <button
            onClick={handleNextPage}
            disabled={offset + EVENTS_PER_PAGE >= catalogTotal}
            className="px-4 py-2 rounded-full border border-white/10 bg-white/5 text-sm font-semibold text-slate-200 transition hover:border-white/30 disabled:opacity-40 disabled:hover:border-white/10"
            type="button"
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
  );
}

function ClockIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 3" />
    </svg>
  );
}
