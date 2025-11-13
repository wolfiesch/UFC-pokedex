"use client";

import { useMemo } from "react";
import { EVENT_TYPE_CONFIGS, type EventType } from "@/lib/event-utils";
import { Check, Globe2, History, MapPin, Sparkles, X } from "lucide-react";

interface EventFiltersProps {
  years: number[];
  locations: string[];
  selectedYears: number[];
  selectedLocations: string[];
  selectedEventTypes: EventType[];
  onYearsChange: (years: number[]) => void;
  onLocationsChange: (locations: string[]) => void;
  onEventTypesChange: (types: EventType[]) => void;
  onClearAll: () => void;
  onClose?: () => void;
}

function toggleValue<T>(collection: T[], value: T): T[] {
  return collection.includes(value)
    ? collection.filter(item => item !== value)
    : [...collection, value];
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
  onClose,
}: EventFiltersProps) {
  const sortedYears = useMemo(() => [...years].sort((a, b) => b - a), [years]);
  const hasActiveFilters =
    selectedYears.length > 0 || selectedLocations.length > 0 || selectedEventTypes.length > 0;

  const renderChip = <T,>(
    label: string,
    value: T,
    isActive: boolean,
    onClick: (value: T) => void
  ) => (
    <button
      key={`${label}-${String(value)}`}
      onClick={() => onClick(value)}
      className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-all ${
        isActive
          ? "border-sky-400/80 bg-sky-500/10 text-sky-100 shadow-[0_0_20px_rgba(56,189,248,0.35)]"
          : "border-white/10 bg-white/5 text-slate-300 hover:border-slate-400/40"
      }`}
    >
      {isActive && <Check className="h-3.5 w-3.5" aria-hidden />}
      <span>{label}</span>
    </button>
  );

  return (
    <div className="space-y-6 rounded-3xl border border-white/10 bg-slate-950/90 p-6 shadow-2xl shadow-black/40 backdrop-blur-xl">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Refine results</p>
          <h3 className="text-lg font-semibold text-white">Build a custom events reel</h3>
        </div>
        <div className="flex items-center gap-2">
          {hasActiveFilters && (
            <button
              onClick={onClearAll}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:border-slate-200/40"
            >
              <X className="h-3.5 w-3.5" aria-hidden />
              Clear all
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="inline-flex items-center gap-2 rounded-full border border-slate-500/30 px-3 py-1.5 text-xs text-slate-300 hover:border-slate-300/50"
            >
              Done
            </button>
          )}
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <section className="space-y-3">
          <header className="flex items-center gap-2 text-slate-200">
            <History className="h-4 w-4 text-slate-400" aria-hidden />
            <span className="text-sm font-semibold uppercase tracking-[0.25em]">Era</span>
          </header>
          <div className="flex flex-wrap gap-2">
            {sortedYears.map((year) =>
              renderChip(`${year}`, year, selectedYears.includes(year), (value) =>
                onYearsChange(toggleValue(selectedYears, value))
              )
            )}
          </div>
        </section>

        <section className="space-y-3">
          <header className="flex items-center gap-2 text-slate-200">
            <Globe2 className="h-4 w-4 text-slate-400" aria-hidden />
            <span className="text-sm font-semibold uppercase tracking-[0.25em]">Destinations</span>
          </header>
          <div className="max-h-48 overflow-y-auto rounded-2xl border border-white/5 bg-slate-900/40 p-3">
            <div className="flex flex-wrap gap-2">
              {locations.map((location) =>
                renderChip(
                  location,
                  location,
                  selectedLocations.includes(location),
                  (value) => onLocationsChange(toggleValue(selectedLocations, value))
                )
              )}
            </div>
          </div>
        </section>
      </div>

      <section className="space-y-3">
        <header className="flex items-center gap-2 text-slate-200">
          <Sparkles className="h-4 w-4 text-slate-400" aria-hidden />
          <span className="text-sm font-semibold uppercase tracking-[0.25em]">Event DNA</span>
        </header>
        <div className="flex flex-wrap gap-2">
          {Object.entries(EVENT_TYPE_CONFIGS).map(([key, config]) =>
            renderChip(
              config.label,
              key as EventType,
              selectedEventTypes.includes(key as EventType),
              (value) => onEventTypesChange(toggleValue(selectedEventTypes, value))
            )
          )}
        </div>
      </section>

      {hasActiveFilters && (
        <div className="border-t border-white/10 pt-4">
          <p className="mb-3 text-xs uppercase tracking-[0.3em] text-slate-400">Active filters</p>
          <div className="flex flex-wrap gap-2">
            {selectedYears.map((year) => (
              <span
                key={`year-${year}`}
                className="inline-flex items-center gap-2 rounded-full border border-sky-400/40 bg-sky-500/10 px-3 py-1 text-xs text-sky-100"
              >
                {year}
                <button
                  onClick={() => onYearsChange(selectedYears.filter((item) => item !== year))}
                  className="rounded-full border border-transparent p-1 text-sky-100/80 hover:border-sky-200/60"
                  aria-label={`Remove ${year} filter`}
                >
                  <X className="h-3 w-3" aria-hidden />
                </button>
              </span>
            ))}
            {selectedLocations.map((location) => (
              <span
                key={`location-${location}`}
                className="inline-flex items-center gap-2 rounded-full border border-emerald-400/40 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-100"
              >
                <MapPin className="h-3.5 w-3.5" aria-hidden />
                {location}
                <button
                  onClick={() =>
                    onLocationsChange(selectedLocations.filter((item) => item !== location))
                  }
                  className="rounded-full border border-transparent p-1 text-emerald-100/80 hover:border-emerald-200/60"
                  aria-label={`Remove ${location} filter`}
                >
                  <X className="h-3 w-3" aria-hidden />
                </button>
              </span>
            ))}
            {selectedEventTypes.map((eventType) => (
              <span
                key={`type-${eventType}`}
                className="inline-flex items-center gap-2 rounded-full border border-purple-400/40 bg-purple-500/10 px-3 py-1 text-xs text-purple-100"
              >
                {EVENT_TYPE_CONFIGS[eventType].label}
                <button
                  onClick={() =>
                    onEventTypesChange(selectedEventTypes.filter((item) => item !== eventType))
                  }
                  className="rounded-full border border-transparent p-1 text-purple-100/80 hover:border-purple-200/60"
                  aria-label={`Remove ${EVENT_TYPE_CONFIGS[eventType].label} filter`}
                >
                  <X className="h-3 w-3" aria-hidden />
                </button>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
