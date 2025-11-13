"use client";

import { useEffect, useMemo, useState } from "react";
import { CalendarCheck, Globe2, MapPin, Settings2, Sparkles, Tags, X } from "lucide-react";
import { EVENT_TYPE_CONFIGS, type EventType } from "@/lib/event-utils";

interface FilterPreset {
  id: string;
  label: string;
  description: string;
  apply: () => void;
}

interface EventFiltersProps {
  years: number[];
  locations: string[];
  selectedYear: number | null;
  selectedLocation: string | null;
  selectedEventType: EventType | null;
  onYearChange: (year: number | null) => void;
  onLocationChange: (location: string | null) => void;
  onEventTypeChange: (eventType: EventType | null) => void;
}

export default function EventFilters({
  years,
  locations,
  selectedYear,
  selectedLocation,
  selectedEventType,
  onYearChange,
  onLocationChange,
  onEventTypeChange,
}: EventFiltersProps) {
  const [openDrawer, setOpenDrawer] = useState<"year" | "location" | "type" | null>(null);
  const [activePresetId, setActivePresetId] = useState<string | null>(null);

  const curatedYears = useMemo<number[]>(() => years.slice(0, 6), [years]);
  const curatedLocations = useMemo<string[]>(() => locations.slice(0, 8), [locations]);

  const hasActiveFilters = Boolean(selectedYear || selectedLocation || selectedEventType);

  const clearFilters = () => {
    onYearChange(null);
    onLocationChange(null);
    onEventTypeChange(null);
    setActivePresetId(null);
  };

  const presets = useMemo<FilterPreset[]>(() => {
    const currentYear = new Date().getFullYear();
    return [
      {
        id: "global-tour",
        label: "Global Tour",
        description: "PPV cards from iconic international arenas",
        apply: () => {
          onEventTypeChange("ppv");
          onLocationChange(null);
          onYearChange(null);
        },
      },
      {
        id: "this-year",
        label: `${currentYear} Highlights`,
        description: "All events from the current calendar year",
        apply: () => {
          onYearChange(currentYear);
          onLocationChange(null);
          onEventTypeChange(null);
        },
      },
      {
        id: "stateside",
        label: "Stateside Swing",
        description: "Fight Nights and ESPN cards across the US",
        apply: () => {
          onEventTypeChange("fight_night");
          const americanCity = locations.find((city) => city.toLowerCase().includes("united states"));
          onLocationChange(americanCity ?? null);
          onYearChange(null);
        },
      },
    ];
  }, [locations, onEventTypeChange, onLocationChange, onYearChange]);

  useEffect(() => {
    if (!hasActiveFilters) {
      setActivePresetId(null);
    }
  }, [hasActiveFilters]);

  const handlePresetApply = (preset: FilterPreset) => {
    preset.apply();
    setActivePresetId(preset.id);
  };

  const renderChip = (
    label: string,
    isActive: boolean,
    onClick: () => void,
    icon?: JSX.Element,
  ) => (
    <button
      key={label}
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition ${
        isActive
          ? "border-cyan-300/70 bg-cyan-400/20 text-cyan-100 shadow-[0_0_15px_rgba(34,211,238,0.25)]"
          : "border-white/10 bg-white/5 text-slate-200 hover:border-white/30 hover:bg-white/10"
      }`}
    >
      {icon}
      {label}
    </button>
  );

  return (
    <div className="space-y-4 rounded-3xl border border-white/10 bg-slate-900/60 p-4 shadow-[0_40px_100px_-60px_rgba(15,23,42,0.9)] backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.35em] text-slate-200/70">
          <Settings2 className="h-4 w-4" aria-hidden="true" />
          Filters
        </div>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            type="button"
            className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-3 py-1 text-xs font-semibold text-slate-100 transition hover:border-white/40 hover:bg-white/10"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
            Clear all
          </button>
        )}
      </div>

      {/* Quick Chips */}
      <div className="flex flex-wrap gap-2">
        {curatedYears.map((year) =>
          renderChip(
            year.toString(),
            selectedYear === year,
            () => onYearChange(selectedYear === year ? null : year),
            <CalendarCheck className="h-3.5 w-3.5" aria-hidden="true" />,
          ),
        )}
        {curatedLocations.map((location) =>
          renderChip(
            location,
            selectedLocation === location,
            () => onLocationChange(selectedLocation === location ? null : location),
            <MapPin className="h-3.5 w-3.5" aria-hidden="true" />,
          ),
        )}
      </div>

      {/* Presets */}
      <div className="flex flex-wrap gap-3">
        {presets.map((preset) => (
          <button
            key={preset.id}
            type="button"
            onClick={() => handlePresetApply(preset)}
            className={`group relative flex flex-col gap-1 rounded-2xl border px-4 py-3 text-left transition ${
              activePresetId === preset.id
                ? "border-emerald-300/60 bg-emerald-400/10 text-emerald-100 shadow-[0_0_30px_rgba(16,185,129,0.25)]"
                : "border-white/10 bg-white/5 text-slate-200 hover:border-white/25 hover:bg-white/10"
            }`}
          >
            <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.25em] text-slate-200/80">
              <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
              {preset.label}
            </span>
            <span className="text-[0.7rem] text-slate-300/80">{preset.description}</span>
          </button>
        ))}
      </div>

      {/* Drawers */}
      <div className="grid gap-3 sm:grid-cols-3">
        {(
          [
            {
              key: "year" as const,
              title: "Year",
              icon: <CalendarCheck className="h-4 w-4" aria-hidden="true" />,
              content: (
                <div className="max-h-48 space-y-2 overflow-y-auto pr-2 text-sm">
                  {years.map((year) => (
                    <button
                      key={year}
                      type="button"
                      onClick={() => onYearChange(selectedYear === year ? null : year)}
                      className={`flex w-full items-center justify-between rounded-xl px-3 py-2 transition ${
                        selectedYear === year
                          ? "bg-cyan-500/20 text-cyan-100"
                          : "bg-white/5 text-slate-200 hover:bg-white/10"
                      }`}
                    >
                      <span>{year}</span>
                      {selectedYear === year && <Tags className="h-3.5 w-3.5" aria-hidden="true" />}
                    </button>
                  ))}
                </div>
              ),
            },
            {
              key: "location" as const,
              title: "Location",
              icon: <Globe2 className="h-4 w-4" aria-hidden="true" />,
              content: (
                <div className="max-h-48 space-y-2 overflow-y-auto pr-2 text-sm">
                  {locations.map((location) => (
                    <button
                      key={location}
                      type="button"
                      onClick={() => onLocationChange(selectedLocation === location ? null : location)}
                      className={`flex w-full items-center justify-between rounded-xl px-3 py-2 transition ${
                        selectedLocation === location
                          ? "bg-rose-500/20 text-rose-100"
                          : "bg-white/5 text-slate-200 hover:bg-white/10"
                      }`}
                    >
                      <span className="truncate text-left">{location}</span>
                      {selectedLocation === location && <Tags className="h-3.5 w-3.5" aria-hidden="true" />}
                    </button>
                  ))}
                </div>
              ),
            },
            {
              key: "type" as const,
              title: "Event Type",
              icon: <Sparkles className="h-4 w-4" aria-hidden="true" />,
              content: (
                <div className="space-y-2">
                  {Object.entries(EVENT_TYPE_CONFIGS).map(([key, config]) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => onEventTypeChange(selectedEventType === key ? null : (key as EventType))}
                      className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm transition ${
                        selectedEventType === key
                          ? "bg-amber-400/20 text-amber-100"
                          : "bg-white/5 text-slate-200 hover:bg-white/10"
                      }`}
                    >
                      <span>{config.label}</span>
                      <span className={`rounded-full px-2 py-0.5 text-[0.65rem] font-semibold ${config.badgeClass}`}>
                        {config.label}
                      </span>
                    </button>
                  ))}
                </div>
              ),
            },
          ] satisfies Array<{
            key: "year" | "location" | "type";
            title: string;
            icon: JSX.Element;
            content: JSX.Element;
          }>
        ).map((drawer) => (
          <div key={drawer.key} className="overflow-hidden rounded-2xl border border-white/10 bg-white/5 backdrop-blur">
            <button
              type="button"
              onClick={() => setOpenDrawer((prev) => (prev === drawer.key ? null : drawer.key))}
              className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left text-sm font-semibold uppercase tracking-[0.2em] text-slate-100"
            >
              <span className="flex items-center gap-2">
                {drawer.icon}
                {drawer.title}
              </span>
              <span className={`transition ${openDrawer === drawer.key ? "rotate-45" : "rotate-0"}`}>
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
            </button>
            <div
              className={`grid transition-[grid-template-rows] duration-300 ease-in-out ${
                openDrawer === drawer.key ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
              }`}
            >
              <div className="overflow-hidden px-4 pb-4">{drawer.content}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Active Filter Chips */}
      {hasActiveFilters && (
        <div className="flex flex-wrap gap-2 pt-2 text-xs text-slate-200">
          {selectedYear && (
            <span className="inline-flex items-center gap-2 rounded-full bg-cyan-500/20 px-3 py-1 font-semibold text-cyan-100">
              <CalendarCheck className="h-3.5 w-3.5" aria-hidden="true" />
              {selectedYear}
              <button type="button" onClick={() => onYearChange(null)} aria-label="Remove year filter">
                <X className="h-3 w-3" aria-hidden="true" />
              </button>
            </span>
          )}
          {selectedLocation && (
            <span className="inline-flex items-center gap-2 rounded-full bg-rose-500/20 px-3 py-1 font-semibold text-rose-100">
              <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
              {selectedLocation.length > 24 ? `${selectedLocation.slice(0, 24)}…` : selectedLocation}
              <button type="button" onClick={() => onLocationChange(null)} aria-label="Remove location filter">
                <X className="h-3 w-3" aria-hidden="true" />
              </button>
            </span>
          )}
          {selectedEventType && (
            <span className="inline-flex items-center gap-2 rounded-full bg-amber-400/20 px-3 py-1 font-semibold text-amber-100">
              <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
              {EVENT_TYPE_CONFIGS[selectedEventType].label}
              <button type="button" onClick={() => onEventTypeChange(null)} aria-label="Remove event type filter">
                <X className="h-3 w-3" aria-hidden="true" />
              </button>
            </span>
          )}
        </div>
      )}
    </div>
  );
}
