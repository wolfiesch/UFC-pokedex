"use client";

import { useMemo, useState, type SVGProps } from "react";
import { ChevronDown, Filter, Globe2, History, MapPin, Sparkles, SquareKanban, Tags } from "lucide-react";
import { EVENT_TYPE_CONFIGS, type EventType } from "@/lib/event-utils";

interface EventFiltersProps {
  years: number[];
  locations: string[];
  selectedYears: number[];
  selectedLocations: string[];
  selectedEventTypes: EventType[];
  onYearsChange: (years: number[]) => void;
  onLocationsChange: (locations: string[]) => void;
  onEventTypesChange: (eventTypes: EventType[]) => void;
}

const savedPresets: Array<{
  label: string;
  description: string;
  tags: string[];
  apply: (toggleYear: (value: number) => void, toggleType: (value: EventType) => void) => void;
}> = [
  {
    label: "PPV Season",
    description: "Flagship numbered cards across the last two years",
    tags: ["PPV", "2024", "2023"],
    apply: (toggleYear, toggleType) => {
      toggleType("ppv");
      toggleYear(new Date().getFullYear());
      toggleYear(new Date().getFullYear() - 1);
    },
  },
  {
    label: "International Fight Week",
    description: "July showcases from Las Vegas",
    tags: ["Vegas", "July"],
    apply: (toggleYear, toggleType) => {
      toggleType("fight_night");
      toggleType("ppv");
      toggleYear(new Date().getFullYear());
    },
  },
];

export default function EventFilters({
  years,
  locations,
  selectedYears,
  selectedLocations,
  selectedEventTypes,
  onYearsChange,
  onLocationsChange,
  onEventTypesChange,
}: EventFiltersProps) {
  const [openDrawer, setOpenDrawer] = useState<"year" | "location" | "type" | null>(null);

  const hasActiveFilters =
    selectedYears.length > 0 || selectedLocations.length > 0 || selectedEventTypes.length > 0;

  const popularYears = useMemo(() => years.slice(-6).reverse(), [years]);
  const popularLocations = useMemo(() => locations.slice(0, 8), [locations]);

  const toggleYear = (value: number) => {
    onYearsChange(
      selectedYears.includes(value)
        ? selectedYears.filter((year) => year !== value)
        : [...selectedYears, value]
    );
  };

  const toggleLocation = (value: string) => {
    onLocationsChange(
      selectedLocations.includes(value)
        ? selectedLocations.filter((location) => location !== value)
        : [...selectedLocations, value]
    );
  };

  const toggleEventType = (value: EventType) => {
    onEventTypesChange(
      selectedEventTypes.includes(value)
        ? selectedEventTypes.filter((type) => type !== value)
        : [...selectedEventTypes, value]
    );
  };

  const clearFilters = () => {
    onYearsChange([]);
    onLocationsChange([]);
    onEventTypesChange([]);
  };

  return (
    <div className="space-y-6 rounded-3xl border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/40 backdrop-blur">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2 text-slate-200">
          <Filter className="h-5 w-5 text-sky-300" aria-hidden />
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-300">Refine the lineup</h3>
            <p className="text-xs text-slate-400">Stack filters to tell the story you want to follow.</p>
          </div>
        </div>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="inline-flex items-center gap-2 rounded-full border border-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-slate-200 transition hover:border-white/40 hover:text-white"
            type="button"
          >
            <History className="h-4 w-4" aria-hidden /> Reset
          </button>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-3">
          <button
            onClick={() => setOpenDrawer(openDrawer === "year" ? null : "year")}
            className="flex w-full items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-left text-sm font-semibold text-slate-100 transition hover:border-white/30 hover:text-white"
            type="button"
          >
            <span className="inline-flex items-center gap-2">
              <SquareKanban className="h-4 w-4 text-sky-300" aria-hidden /> Active years
            </span>
            <ChevronDown
              className={`h-4 w-4 transition-transform ${openDrawer === "year" ? "rotate-180" : ""}`}
              aria-hidden
            />
          </button>
          {openDrawer === "year" && (
            <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-4 shadow-inner">
              <p className="mb-3 text-xs uppercase tracking-[0.3em] text-slate-400">Quick picks</p>
              <div className="flex flex-wrap gap-2">
                {popularYears.map((year) => (
                  <button
                    key={year}
                    onClick={() => toggleYear(year)}
                    className={`rounded-full px-4 py-1 text-xs font-semibold transition ${
                      selectedYears.includes(year)
                        ? "bg-sky-500/20 text-sky-200 ring-1 ring-sky-400/60"
                        : "bg-white/5 text-slate-300 hover:bg-white/10"
                    }`}
                    type="button"
                  >
                    {year}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-3">
          <button
            onClick={() => setOpenDrawer(openDrawer === "location" ? null : "location")}
            className="flex w-full items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-left text-sm font-semibold text-slate-100 transition hover:border-white/30 hover:text-white"
            type="button"
          >
            <span className="inline-flex items-center gap-2">
              <MapPin className="h-4 w-4 text-emerald-300" aria-hidden /> Destination cities
            </span>
            <ChevronDown
              className={`h-4 w-4 transition-transform ${openDrawer === "location" ? "rotate-180" : ""}`}
              aria-hidden
            />
          </button>
          {openDrawer === "location" && (
            <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-4 shadow-inner">
              <p className="mb-3 text-xs uppercase tracking-[0.3em] text-slate-400">Hotspots</p>
              <div className="flex flex-wrap gap-2">
                {popularLocations.map((location) => (
                  <button
                    key={location}
                    onClick={() => toggleLocation(location)}
                    className={`rounded-full px-4 py-1 text-xs font-semibold transition ${
                      selectedLocations.includes(location)
                        ? "bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-400/60"
                        : "bg-white/5 text-slate-300 hover:bg-white/10"
                    }`}
                    type="button"
                  >
                    {location}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-3">
          <button
            onClick={() => setOpenDrawer(openDrawer === "type" ? null : "type")}
            className="flex w-full items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-left text-sm font-semibold text-slate-100 transition hover:border-white/30 hover:text-white"
            type="button"
          >
            <span className="inline-flex items-center gap-2">
              <Tags className="h-4 w-4 text-amber-300" aria-hidden /> Event identity
            </span>
            <ChevronDown
              className={`h-4 w-4 transition-transform ${openDrawer === "type" ? "rotate-180" : ""}`}
              aria-hidden
            />
          </button>
          {openDrawer === "type" && (
            <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-4 shadow-inner">
              <div className="flex flex-wrap gap-2">
                {Object.entries(EVENT_TYPE_CONFIGS).map(([key, config]) => (
                  <button
                    key={key}
                    onClick={() => toggleEventType(key as EventType)}
                    className={`rounded-full px-4 py-1 text-xs font-semibold transition ${
                      selectedEventTypes.includes(key as EventType)
                        ? "bg-amber-500/20 text-amber-200 ring-1 ring-amber-400/60"
                        : "bg-white/5 text-slate-300 hover:bg-white/10"
                    }`}
                    type="button"
                  >
                    {config.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {savedPresets.map((preset) => (
          <button
            key={preset.label}
            onClick={() => preset.apply(toggleYear, toggleEventType)}
            className="flex flex-col gap-2 rounded-2xl border border-white/10 bg-gradient-to-br from-white/5 via-white/0 to-white/10 px-4 py-4 text-left transition hover:border-white/40 hover:shadow-lg"
            type="button"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-white">{preset.label}</p>
                <p className="text-xs text-slate-400">{preset.description}</p>
              </div>
              <Sparkles className="h-5 w-5 text-sky-300" aria-hidden />
            </div>
            <div className="flex flex-wrap gap-2">
              {preset.tags.map((tag) => (
                <span key={tag} className="rounded-full bg-white/10 px-3 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-slate-200">
                  {tag}
                </span>
              ))}
            </div>
          </button>
        ))}
      </div>

      {hasActiveFilters && (
        <div className="rounded-2xl border border-white/5 bg-white/5 p-4">
          <p className="mb-3 text-xs uppercase tracking-[0.3em] text-slate-400">Active filters</p>
          <div className="flex flex-wrap gap-2">
            {selectedYears.map((year) => (
              <button
                key={`year-${year}`}
                onClick={() => toggleYear(year)}
                className="inline-flex items-center gap-2 rounded-full bg-sky-500/15 px-3 py-1 text-xs font-semibold text-sky-200 transition hover:bg-sky-500/25"
                type="button"
              >
                <CalendarRangeIcon aria-hidden className="h-3.5 w-3.5" /> {year}
              </button>
            ))}
            {selectedLocations.map((location) => (
              <button
                key={`location-${location}`}
                onClick={() => toggleLocation(location)}
                className="inline-flex items-center gap-2 rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-semibold text-emerald-200 transition hover:bg-emerald-500/25"
                type="button"
              >
                <Globe2 className="h-3.5 w-3.5" aria-hidden />
                {location.length > 24 ? `${location.slice(0, 24)}…` : location}
              </button>
            ))}
            {selectedEventTypes.map((type) => (
              <button
                key={`type-${type}`}
                onClick={() => toggleEventType(type)}
                className="inline-flex items-center gap-2 rounded-full bg-amber-500/15 px-3 py-1 text-xs font-semibold text-amber-200 transition hover:bg-amber-500/25"
                type="button"
              >
                <Tags className="h-3.5 w-3.5" aria-hidden />
                {EVENT_TYPE_CONFIGS[type].label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CalendarRangeIcon(props: SVGProps<SVGSVGElement>) {
  // Lightweight inline icon to keep the chip compact while meeting the "iconography everywhere" brief.
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
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
      <path d="m9 16 2 2 4-4" />
    </svg>
  );
}
