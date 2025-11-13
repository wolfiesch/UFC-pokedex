"use client";

import { EVENT_TYPE_CONFIGS, type EventType } from "@/lib/event-utils";

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
  const hasActiveFilters =
    selectedYear || selectedLocation || selectedEventType;

  const clearFilters = () => {
    onYearChange(null);
    onLocationChange(null);
    onEventTypeChange(null);
  };

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800 p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Filters</h3>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="text-sm text-blue-400 transition-colors hover:text-blue-300"
          >
            Clear all
          </button>
        )}
      </div>

      <div className="space-y-6">
        {/* Year Filter */}
        <div>
          <label className="mb-2 block text-sm font-medium text-gray-400">
            Year
          </label>
          <select
            value={selectedYear?.toString() || ""}
            onChange={(e) =>
              onYearChange(e.target.value ? parseInt(e.target.value) : null)
            }
            className="w-full rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-white transition-all focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-600"
          >
            <option value="">All years</option>
            {years.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>

        {/* Event Type Filter */}
        <div>
          <label className="mb-2 block text-sm font-medium text-gray-400">
            Event Type
          </label>
          <select
            value={selectedEventType || ""}
            onChange={(e) =>
              onEventTypeChange((e.target.value as EventType) || null)
            }
            className="w-full rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-white transition-all focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-600"
          >
            <option value="">All types</option>
            {Object.entries(EVENT_TYPE_CONFIGS).map(([key, config]) => (
              <option key={key} value={key}>
                {config.label}
              </option>
            ))}
          </select>
        </div>

        {/* Location Filter */}
        <div>
          <label className="mb-2 block text-sm font-medium text-gray-400">
            Location
          </label>
          <select
            value={selectedLocation || ""}
            onChange={(e) => onLocationChange(e.target.value || null)}
            className="w-full rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-white transition-all focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-600"
          >
            <option value="">All locations</option>
            {locations.map((location) => (
              <option key={location} value={location}>
                {location}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Active Filters Display */}
      {hasActiveFilters && (
        <div className="mt-4 border-t border-gray-700 pt-4">
          <div className="flex flex-wrap gap-2">
            {selectedYear && (
              <span className="flex items-center gap-1 rounded-full bg-blue-900 px-2 py-1 text-xs text-blue-300">
                {selectedYear}
                <button
                  onClick={() => onYearChange(null)}
                  className="transition-colors hover:text-blue-100"
                  aria-label="Remove year filter"
                >
                  ✕
                </button>
              </span>
            )}
            {selectedEventType && (
              <span className="flex items-center gap-1 rounded-full bg-purple-900 px-2 py-1 text-xs text-purple-300">
                {EVENT_TYPE_CONFIGS[selectedEventType].label}
                <button
                  onClick={() => onEventTypeChange(null)}
                  className="transition-colors hover:text-purple-100"
                  aria-label="Remove event type filter"
                >
                  ✕
                </button>
              </span>
            )}
            {selectedLocation && (
              <span className="flex items-center gap-1 rounded-full bg-green-900 px-2 py-1 text-xs text-green-300">
                {selectedLocation.length > 20
                  ? `${selectedLocation.substring(0, 20)}...`
                  : selectedLocation}
                <button
                  onClick={() => onLocationChange(null)}
                  className="transition-colors hover:text-green-100"
                  aria-label="Remove location filter"
                >
                  ✕
                </button>
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
