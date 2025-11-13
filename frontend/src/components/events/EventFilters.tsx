"use client";

import { useMemo } from "react";
import {
  CalendarCheck,
  Check,
  Filter,
  Globe2,
  Layers3,
  MapPin,
  Sparkles,
  X,
} from "lucide-react";
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
  onClearAll: () => void;
}

export default function EventFilters({
  years,
  locations,
  selectedYears,
  selectedLocations,
  selectedEventTypes,
  onYearsChange,
  onLocationsChange,
  onEventTypesChange,
  onClearAll,
}: EventFiltersProps) {
  const popularYears = useMemo(() => {
    return [...years].sort((a, b) => b - a).slice(0, 4);
  }, [years]);

  const popularCities = useMemo(() => {
    return locations.slice(0, 6);
  }, [locations]);

  const toggleYear = (year: number) => {
    onYearsChange(
      selectedYears.includes(year)
        ? selectedYears.filter((value) => value !== year)
        : [...selectedYears, year],
    );
  };

  const toggleLocation = (location: string) => {
    onLocationsChange(
      selectedLocations.includes(location)
        ? selectedLocations.filter((value) => value !== location)
        : [...selectedLocations, location],
    );
  };

  const toggleEventType = (eventType: EventType) => {
    onEventTypesChange(
      selectedEventTypes.includes(eventType)
        ? selectedEventTypes.filter((value) => value !== eventType)
        : [...selectedEventTypes, eventType],
    );
  };

  const presets = useMemo(
    () => [
      {
        id: "headline-ppv",
        label: "This Year's PPVs",
        description: "Spotlight premium championship nights in the current calendar year.",
        apply: () => {
          onYearsChange([new Date().getFullYear()]);
          onEventTypesChange(["ppv"]);
          onLocationsChange([]);
        },
      },
      {
        id: "international",
        label: "International Swing",
        description: "Capture events staged outside the United States for global tours.",
        apply: () => {
          const internationalStops = locations.filter((location) => {
            const normalized = location.toLowerCase();
            return !normalized.includes("usa") && !normalized.includes("united states");
          });
          onLocationsChange(internationalStops.slice(0, 8));
          onEventTypesChange([]);
        },
      },
      {
        id: "vegas",
        label: "Vegas Residency",
        description: "Zero in on Apex and Strip showdowns under the desert lights.",
        apply: () => {
          const vegasShows = locations.filter((location) =>
            location.toLowerCase().includes("las vegas"),
          );
          onLocationsChange(vegasShows);
          onYearsChange([]);
        },
      },
    ],
    [locations, onEventTypesChange, onLocationsChange, onYearsChange],
  );

  const hasActiveFilters =
    selectedYears.length > 0 || selectedLocations.length > 0 || selectedEventTypes.length > 0;

  return (
    <div className="space-y-6 text-white">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.3em] text-white/60">
          <Filter className="h-4 w-4 text-emerald-300" aria-hidden="true" />
          Refine spotlight
        </div>
        {hasActiveFilters && (
          <button
            onClick={onClearAll}
            className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-white/70 transition hover:border-white/30 hover:bg-white/10"
          >
            <X className="h-3 w-3" aria-hidden="true" />
            Clear all
          </button>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr_1fr]">
        <section className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.25em] text-white/60">
            <Sparkles className="h-4 w-4 text-amber-300" aria-hidden="true" />
            Saved presets
          </div>
          <div className="mt-4 space-y-3">
            {presets.map((preset) => (
              <button
                key={preset.id}
                onClick={preset.apply}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-left transition hover:border-white/30 hover:bg-white/10"
              >
                <p className="text-sm font-semibold text-white">{preset.label}</p>
                <p className="text-xs text-white/70">{preset.description}</p>
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.25em] text-white/60">
            <CalendarCheck className="h-4 w-4 text-emerald-300" aria-hidden="true" />
            Rapid years
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {popularYears.map((year) => {
              const isActive = selectedYears.includes(year);
              return (
                <button
                  key={year}
                  onClick={() => toggleYear(year)}
                  className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold transition ${
                    isActive
                      ? "border-emerald-300 bg-emerald-400/20 text-emerald-100"
                      : "border-white/10 bg-white/5 text-white/70 hover:border-white/30 hover:bg-white/10"
                  }`}
                >
                  {isActive && <Check className="h-3 w-3" aria-hidden="true" />}
                  {year}
                </button>
              );
            })}
          </div>
          <div className="mt-6">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-white/60">All years</p>
            <div className="mt-3 grid max-h-32 grid-cols-2 gap-2 overflow-y-auto pr-1 text-xs">
              {years.map((year) => {
                const isActive = selectedYears.includes(year);
                return (
                  <button
                    key={`full-${year}`}
                    onClick={() => toggleYear(year)}
                    className={`flex items-center justify-between rounded-lg border px-3 py-2 transition ${
                      isActive
                        ? "border-emerald-300 bg-emerald-400/20 text-emerald-100"
                        : "border-white/10 bg-white/5 text-white/70 hover:border-white/30 hover:bg-white/10"
                    }`}
                  >
                    <span>{year}</span>
                    {isActive && <Check className="h-3 w-3" aria-hidden="true" />}
                  </button>
                );
              })}
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.25em] text-white/60">
            <MapPin className="h-4 w-4 text-sky-300" aria-hidden="true" />
            Marquee cities
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {popularCities.map((city) => {
              const isActive = selectedLocations.includes(city);
              return (
                <button
                  key={city}
                  onClick={() => toggleLocation(city)}
                  className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold transition ${
                    isActive
                      ? "border-sky-300 bg-sky-400/20 text-sky-100"
                      : "border-white/10 bg-white/5 text-white/70 hover:border-white/30 hover:bg-white/10"
                  }`}
                >
                  {isActive && <Check className="h-3 w-3" aria-hidden="true" />}
                  {city.split(",")[0]}
                </button>
              );
            })}
          </div>
          <div className="mt-6">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-white/60">All locales</p>
            <div className="mt-3 max-h-32 space-y-2 overflow-y-auto pr-1 text-xs">
              {locations.map((location) => {
                const isActive = selectedLocations.includes(location);
                return (
                  <button
                    key={location}
                    onClick={() => toggleLocation(location)}
                    className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 transition ${
                      isActive
                        ? "border-sky-300 bg-sky-400/20 text-sky-100"
                        : "border-white/10 bg-white/5 text-white/70 hover:border-white/30 hover:bg-white/10"
                    }`}
                  >
                    <span className="truncate">{location}</span>
                    {isActive && <Check className="h-3 w-3 flex-shrink-0" aria-hidden="true" />}
                  </button>
                );
              })}
            </div>
          </div>
        </section>
      </div>

      <section className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.25em] text-white/60">
          <Layers3 className="h-4 w-4 text-purple-300" aria-hidden="true" />
          Event formats
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {Object.entries(EVENT_TYPE_CONFIGS).map(([key, config]) => {
            const typedKey = key as EventType;
            const isActive = selectedEventTypes.includes(typedKey);
            return (
              <button
                key={key}
                onClick={() => toggleEventType(typedKey)}
                className={`flex items-center justify-between rounded-xl border px-4 py-3 text-left transition ${
                  isActive
                    ? `${config.badgeClass} border-white/40 text-white`
                    : "border-white/10 bg-white/5 text-white/70 hover:border-white/30 hover:bg-white/10"
                }`}
              >
                <span className="text-sm font-semibold">{config.label}</span>
                {isActive && <Globe2 className="h-4 w-4" aria-hidden="true" />}
              </button>
            );
          })}
        </div>
      </section>

      {hasActiveFilters && (
        <div className="space-y-3 rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-white/60">Active filters</p>
          <div className="flex flex-wrap gap-2">
            {selectedYears.map((year) => (
              <span
                key={`active-year-${year}`}
                className="inline-flex items-center gap-2 rounded-full border border-emerald-300/60 bg-emerald-400/20 px-3 py-1 text-xs font-semibold text-emerald-100"
              >
                <CalendarCheck className="h-3 w-3" aria-hidden="true" />
                {year}
                <button
                  onClick={() => toggleYear(year)}
                  className="rounded-full bg-emerald-500/30 p-1 text-emerald-50 transition hover:bg-emerald-500/60"
                  aria-label={`Remove year ${year}`}
                >
                  <X className="h-3 w-3" aria-hidden="true" />
                </button>
              </span>
            ))}
            {selectedLocations.map((location) => (
              <span
                key={`active-location-${location}`}
                className="inline-flex items-center gap-2 rounded-full border border-sky-300/60 bg-sky-400/20 px-3 py-1 text-xs font-semibold text-sky-100"
              >
                <MapPin className="h-3 w-3" aria-hidden="true" />
                {location}
                <button
                  onClick={() => toggleLocation(location)}
                  className="rounded-full bg-sky-500/30 p-1 text-sky-50 transition hover:bg-sky-500/60"
                  aria-label={`Remove location ${location}`}
                >
                  <X className="h-3 w-3" aria-hidden="true" />
                </button>
              </span>
            ))}
            {selectedEventTypes.map((eventType) => (
              <span
                key={`active-type-${eventType}`}
                className="inline-flex items-center gap-2 rounded-full border border-purple-300/60 bg-purple-500/20 px-3 py-1 text-xs font-semibold text-purple-100"
              >
                <Layers3 className="h-3 w-3" aria-hidden="true" />
                {EVENT_TYPE_CONFIGS[eventType].label}
                <button
                  onClick={() => toggleEventType(eventType)}
                  className="rounded-full bg-purple-500/30 p-1 text-purple-50 transition hover:bg-purple-500/60"
                  aria-label={`Remove event type ${EVENT_TYPE_CONFIGS[eventType].label}`}
                >
                  <X className="h-3 w-3" aria-hidden="true" />
                </button>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
