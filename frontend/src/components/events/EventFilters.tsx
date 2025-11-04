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
  const hasActiveFilters = selectedYear || selectedLocation || selectedEventType;

  const clearFilters = () => {
    onYearChange(null);
    onLocationChange(null);
    onEventTypeChange(null);
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Filters</h3>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            Clear all
          </button>
        )}
      </div>

      <div className="space-y-6">
        {/* Year Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">Year</label>
          <select
            value={selectedYear?.toString() || ""}
            onChange={(e) => onYearChange(e.target.value ? parseInt(e.target.value) : null)}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all"
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
          <label className="block text-sm font-medium text-gray-400 mb-2">Event Type</label>
          <select
            value={selectedEventType || ""}
            onChange={(e) => onEventTypeChange((e.target.value as EventType) || null)}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all"
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
          <label className="block text-sm font-medium text-gray-400 mb-2">Location</label>
          <select
            value={selectedLocation || ""}
            onChange={(e) => onLocationChange(e.target.value || null)}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all"
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
        <div className="mt-4 pt-4 border-t border-gray-700">
          <div className="flex flex-wrap gap-2">
            {selectedYear && (
              <span className="px-2 py-1 bg-blue-900 text-blue-300 text-xs rounded-full flex items-center gap-1">
                {selectedYear}
                <button
                  onClick={() => onYearChange(null)}
                  className="hover:text-blue-100 transition-colors"
                  aria-label="Remove year filter"
                >
                  ✕
                </button>
              </span>
            )}
            {selectedEventType && (
              <span className="px-2 py-1 bg-purple-900 text-purple-300 text-xs rounded-full flex items-center gap-1">
                {EVENT_TYPE_CONFIGS[selectedEventType].label}
                <button
                  onClick={() => onEventTypeChange(null)}
                  className="hover:text-purple-100 transition-colors"
                  aria-label="Remove event type filter"
                >
                  ✕
                </button>
              </span>
            )}
            {selectedLocation && (
              <span className="px-2 py-1 bg-green-900 text-green-300 text-xs rounded-full flex items-center gap-1">
                {selectedLocation.length > 20 ? `${selectedLocation.substring(0, 20)}...` : selectedLocation}
                <button
                  onClick={() => onLocationChange(null)}
                  className="hover:text-green-100 transition-colors"
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
