"use client";

import { useMemo, useState, type ReactNode } from "react";
import clsx from "clsx";
import EventSearch from "@/components/events/EventSearch";
import { EVENT_TYPE_CONFIGS, type EventType } from "@/lib/event-utils";
import {
  CalendarDays,
  ChevronDown,
  ChevronUp,
  Filter,
  Flame,
  Grid2x2,
  Layers,
  ListOrdered,
  MapPin,
  Save,
  SlidersHorizontal,
  Sparkles,
  X,
} from "lucide-react";

type ViewMode = "grid" | "timeline";

export interface SavedFilterPreset {
  id: string;
  name: string;
  description: string;
  filters: {
    years: number[];
    locations: string[];
    eventTypes: EventType[];
    status?: "all" | "upcoming" | "completed";
  };
}

interface EventFiltersProps {
  years: number[];
  locations: string[];
  selectedYears: number[];
  selectedLocations: string[];
  selectedEventTypes: EventType[];
  statusFilter: "all" | "upcoming" | "completed";
  viewMode: ViewMode;
  searchQuery: string;
  popularYears: number[];
  popularLocations: string[];
  presets: SavedFilterPreset[];
  onSearchChange: (value: string) => void;
  onToggleYear: (year: number) => void;
  onToggleLocation: (location: string) => void;
  onToggleEventType: (eventType: EventType) => void;
  onStatusFilterChange: (status: "all" | "upcoming" | "completed") => void;
  onViewModeChange: (mode: ViewMode) => void;
  onClearAll: () => void;
  onApplyPreset: (preset: SavedFilterPreset) => void;
  onRemoveFilterChip: (type: "year" | "location" | "eventType", value: number | string) => void;
  hasActiveFilters: boolean;
}

type DrawerKey = "years" | "locations" | "types";

const STATUS_SEGMENTS: Array<{
  id: "all" | "upcoming" | "completed";
  label: string;
  description: string;
  icon: typeof CalendarDays;
}> = [
  {
    id: "all",
    label: "All",
    description: "Full event atlas",
    icon: CalendarDays,
  },
  {
    id: "upcoming",
    label: "Upcoming",
    description: "Future fight cards",
    icon: Sparkles,
  },
  {
    id: "completed",
    label: "Archive",
    description: "Results locked in",
    icon: Flame,
  },
];

export default function EventFilters({
  years,
  locations,
  selectedYears,
  selectedLocations,
  selectedEventTypes,
  statusFilter,
  viewMode,
  searchQuery,
  popularYears,
  popularLocations,
  presets,
  onSearchChange,
  onToggleYear,
  onToggleLocation,
  onToggleEventType,
  onStatusFilterChange,
  onViewModeChange,
  onClearAll,
  onApplyPreset,
  onRemoveFilterChip,
  hasActiveFilters,
}: EventFiltersProps) {
  const [openDrawer, setOpenDrawer] = useState<DrawerKey | null>(null);

  const toggleDrawer = (drawer: DrawerKey) => {
    setOpenDrawer((current) => (current === drawer ? null : drawer));
  };

  const activeFilterChips = useMemo(() => {
    const chips: Array<{
      id: string;
      label: string;
      tone: "year" | "location" | "eventType";
      icon: typeof CalendarDays;
      value: string | number;
    }> = [];

    selectedYears.forEach((year) => {
      chips.push({
        id: `year-${year}`,
        label: `${year}`,
        tone: "year",
        icon: CalendarDays,
        value: year,
      });
    });

    selectedLocations.forEach((location) => {
      chips.push({
        id: `location-${location}`,
        label: location,
        tone: "location",
        icon: MapPin,
        value: location,
      });
    });

    selectedEventTypes.forEach((eventType) => {
      chips.push({
        id: `type-${eventType}`,
        label: EVENT_TYPE_CONFIGS[eventType]?.label ?? eventType,
        tone: "eventType",
        icon: SlidersHorizontal,
        value: eventType,
      });
    });

    return chips;
  }, [selectedYears, selectedLocations, selectedEventTypes]);

  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-[0_12px_50px_rgba(15,23,42,0.4)] backdrop-blur-xl">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex-1">
          <EventSearch value={searchQuery} onChange={onSearchChange} />
        </div>

        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="flex rounded-full border border-white/10 bg-black/30 p-1 shadow-inner backdrop-blur">
            {STATUS_SEGMENTS.map(({ id, label, icon: Icon }) => {
              const isActive = statusFilter === id;
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => onStatusFilterChange(id)}
                  className={clsx(
                    "group inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition",
                    isActive
                      ? "bg-gradient-to-r from-amber-500/80 to-orange-500/80 text-white shadow-lg"
                      : "text-white/60 hover:text-white",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span>{label}</span>
                </button>
              );
            })}
          </div>

          <div className="flex rounded-full border border-white/10 bg-black/30 p-1 shadow-inner backdrop-blur">
            <button
              type="button"
              onClick={() => onViewModeChange("grid")}
              className={clsx(
                "inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition",
                viewMode === "grid"
                  ? "bg-white/20 text-white shadow-lg"
                  : "text-white/60 hover:text-white",
              )}
            >
              <Grid2x2 className="h-4 w-4" />
              Grid
            </button>
            <button
              type="button"
              onClick={() => onViewModeChange("timeline")}
              className={clsx(
                "inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition",
                viewMode === "timeline"
                  ? "bg-white/20 text-white shadow-lg"
                  : "text-white/60 hover:text-white",
              )}
            >
              <ListOrdered className="h-4 w-4" />
              Timeline
            </button>
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <div className="flex flex-wrap items-center gap-2">
            <Filter className="h-4 w-4 text-white/50" />
            <span className="text-xs uppercase tracking-[0.35em] text-white/50">Quick picks</span>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {popularYears.map((year) => {
              const active = selectedYears.includes(year);
              return (
                <button
                  key={year}
                  type="button"
                  onClick={() => onToggleYear(year)}
                  className={clsx(
                    "rounded-full px-3 py-1 text-sm transition",
                    active
                      ? "bg-white/25 text-white shadow"
                      : "bg-white/10 text-white/70 hover:bg-white/20 hover:text-white",
                  )}
                >
                  {year}
                </button>
              );
            })}

            {popularLocations.map((location) => {
              const active = selectedLocations.includes(location);
              return (
                <button
                  key={location}
                  type="button"
                  onClick={() => onToggleLocation(location)}
                  className={clsx(
                    "rounded-full px-3 py-1 text-sm transition",
                    active
                      ? "bg-white/25 text-white shadow"
                      : "bg-white/10 text-white/70 hover:bg-white/20 hover:text-white",
                  )}
                >
                  {location}
                </button>
              );
            })}
          </div>
        </div>

        <div className="lg:col-span-2">
          <div className="flex flex-wrap items-center gap-2">
            <Save className="h-4 w-4 text-white/50" />
            <span className="text-xs uppercase tracking-[0.35em] text-white/50">Saved presets</span>
          </div>
          <div className="mt-3 grid gap-2">
            {presets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => onApplyPreset(preset)}
                className="flex flex-col rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-left shadow-inner transition hover:border-white/20 hover:bg-black/40"
              >
                <span className="text-sm font-semibold text-white">{preset.name}</span>
                <span className="text-xs text-white/50">{preset.description}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-8 grid gap-4 lg:grid-cols-3">
        <FilterDrawer
          label="Years"
          description="Stack eras and rivalries"
          icon={Layers}
          isOpen={openDrawer === "years"}
          onToggle={() => toggleDrawer("years")}
        >
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {years.map((year) => {
              const active = selectedYears.includes(year);
              return (
                <button
                  key={year}
                  type="button"
                  onClick={() => onToggleYear(year)}
                  className={clsx(
                    "rounded-xl border px-3 py-2 text-sm transition",
                    active
                      ? "border-white/40 bg-white/20 text-white shadow"
                      : "border-white/10 bg-white/5 text-white/70 hover:border-white/30 hover:text-white",
                  )}
                >
                  {year}
                </button>
              );
            })}
          </div>
        </FilterDrawer>

        <FilterDrawer
          label="Cities"
          description="Spotlight octagon destinations"
          icon={MapPin}
          isOpen={openDrawer === "locations"}
          onToggle={() => toggleDrawer("locations")}
        >
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {locations.map((location) => {
              const active = selectedLocations.includes(location);
              return (
                <button
                  key={location}
                  type="button"
                  onClick={() => onToggleLocation(location)}
                  className={clsx(
                    "rounded-xl border px-3 py-2 text-left text-sm transition",
                    active
                      ? "border-white/40 bg-white/20 text-white shadow"
                      : "border-white/10 bg-white/5 text-white/70 hover:border-white/30 hover:text-white",
                  )}
                >
                  {location}
                </button>
              );
            })}
          </div>
        </FilterDrawer>

        <FilterDrawer
          label="Event identity"
          description="Tune the promotion vibe"
          icon={SlidersHorizontal}
          isOpen={openDrawer === "types"}
          onToggle={() => toggleDrawer("types")}
        >
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {Object.entries(EVENT_TYPE_CONFIGS).map(([key, config]) => {
              const type = key as EventType;
              const active = selectedEventTypes.includes(type);
              const shortLabel = config.label.slice(0, 3).toUpperCase();
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => onToggleEventType(type)}
                  className={clsx(
                    "flex items-center justify-between rounded-xl border px-3 py-2 text-left text-sm transition",
                    active
                      ? "border-white/40 bg-white/20 text-white shadow"
                      : "border-white/10 bg-white/5 text-white/70 hover:border-white/30 hover:text-white",
                  )}
                >
                  <span>{config.label}</span>
                  <span className="text-xs uppercase tracking-widest text-white/40">{shortLabel}</span>
                </button>
              );
            })}
          </div>
        </FilterDrawer>
      </div>

      <div className="mt-8 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          {activeFilterChips.length > 0 ? (
            activeFilterChips.map(({ id, label, tone, icon: Icon, value }) => (
              <span
                key={id}
                className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs text-white"
              >
                <Icon className="h-3.5 w-3.5" />
                <span className="max-w-[9rem] truncate">{label}</span>
                <button
                  type="button"
                  onClick={() => onRemoveFilterChip(tone, value)}
                  className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-white/10 text-white/70 transition hover:bg-white/20 hover:text-white"
                  aria-label={`Remove ${tone} filter`}
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))
          ) : (
            <span className="flex items-center gap-2 text-xs uppercase tracking-[0.4em] text-white/40">
              <Layers className="h-3.5 w-3.5" />
              Tune filters to craft your event story
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {hasActiveFilters && (
            <button
              type="button"
              onClick={onClearAll}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-sm font-medium text-white/80 transition hover:border-white/20 hover:bg-white/20 hover:text-white"
            >
              <X className="h-4 w-4" />
              Clear all
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

interface FilterDrawerProps {
  label: string;
  description: string;
  icon: typeof Layers;
  isOpen: boolean;
  onToggle: () => void;
  children: ReactNode;
}

function FilterDrawer({
  label,
  description,
  icon: Icon,
  isOpen,
  onToggle,
  children,
}: FilterDrawerProps) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/30 p-4 shadow-inner backdrop-blur">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between text-left text-sm font-semibold text-white"
      >
        <span className="flex items-center gap-3">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-white/10">
            <Icon className="h-4 w-4 text-white/80" />
          </span>
          <span>
            <span className="block text-sm font-semibold text-white">{label}</span>
            <span className="block text-xs text-white/50">{description}</span>
          </span>
        </span>
        {isOpen ? (
          <ChevronUp className="h-4 w-4 text-white/60" />
        ) : (
          <ChevronDown className="h-4 w-4 text-white/60" />
        )}
      </button>

      {isOpen && <div className="mt-4 space-y-3">{children}</div>}
    </div>
  );
}
