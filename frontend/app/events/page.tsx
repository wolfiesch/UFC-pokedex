"use client";

import { useState, useEffect } from "react";
import EventCard from "@/components/events/EventCard";
import EventSearch from "@/components/events/EventSearch";
import EventFilters from "@/components/events/EventFilters";
import EventTimeline from "@/components/events/EventTimeline";
import type { EventType } from "@/lib/event-utils";

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

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading events...</div>
      </div>
    );
  }

  const hasActiveFilters = searchQuery || selectedYear || selectedLocation || selectedEventType;
  const showPagination = statusFilter !== "upcoming" && total > EVENTS_PER_PAGE && !hasActiveFilters;

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-6">UFC Events</h1>

        {/* Search Bar */}
        <div className="mb-6">
          <EventSearch
            value={searchQuery}
            onChange={handleSearchChange}
            placeholder="Search by event name, location, or fighter..."
          />
        </div>

        {/* Filter Tabs and View Toggle */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => handleFilterChange("all")}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                statusFilter === "all"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              All Events ({total})
            </button>
            <button
              onClick={() => handleFilterChange("upcoming")}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                statusFilter === "upcoming"
                  ? "bg-green-600 text-white"
                  : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              Upcoming
            </button>
            <button
              onClick={() => handleFilterChange("completed")}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                statusFilter === "completed"
                  ? "bg-gray-600 text-white"
                  : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              Completed
            </button>
          </div>

          <div className="flex gap-2">
            {/* Filters Toggle */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
                showFilters || hasActiveFilters
                  ? "bg-purple-600 text-white"
                  : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              <span>🎛️</span>
              <span>Filters</span>
              {hasActiveFilters && <span className="bg-purple-800 px-2 py-0.5 rounded-full text-xs">Active</span>}
            </button>

            {/* View Mode Toggle */}
            <div className="flex gap-1 bg-gray-700 rounded-lg p-1">
              <button
                onClick={() => setViewMode("grid")}
                className={`px-3 py-1 rounded-md font-medium transition-colors ${
                  viewMode === "grid"
                    ? "bg-gray-600 text-white"
                    : "text-gray-400 hover:text-gray-200"
                }`}
                title="Grid view"
              >
                ▦
              </button>
              <button
                onClick={() => setViewMode("timeline")}
                className={`px-3 py-1 rounded-md font-medium transition-colors ${
                  viewMode === "timeline"
                    ? "bg-gray-600 text-white"
                    : "text-gray-400 hover:text-gray-200"
                }`}
                title="Timeline view"
              >
                ≡
              </button>
            </div>
          </div>
        </div>

        {/* Filter Panel */}
        {showFilters && (
          <div className="mb-6">
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
        )}
      </div>

      {/* Events Display */}
      {viewMode === "grid" ? (
        <div className="grid grid-cols-1 gap-4">
          {events.map((event) => (
            <EventCard key={event.event_id} event={event} />
          ))}
        </div>
      ) : (
        <EventTimeline events={events} />
      )}

      {/* Pagination */}
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
            Page {Math.floor(offset / EVENTS_PER_PAGE) + 1} of{" "}
            {Math.ceil(total / EVENTS_PER_PAGE)}
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
          {hasActiveFilters && (
            <p className="text-sm">Try adjusting your search or filters.</p>
          )}
        </div>
      )}
    </div>
  );
}
