"use client";

import Link from "next/link";
import {
  detectEventType,
  getEventTypeConfig,
  normalizeEventType,
  type EventType,
} from "@/lib/event-utils";

interface EventListItem {
  event_id: string;
  name: string;
  date: string;
  location: string | null;
  status: string;
  event_type?: EventType | string | null;
}

interface RelatedEventsWidgetProps {
  currentEventId: string;
  relatedEvents: EventListItem[];
  reason?: "location" | "timeframe" | "general";
}

/**
 * Widget displaying related events (same location or nearby in time)
 */
export default function RelatedEventsWidget({
  currentEventId,
  relatedEvents,
  reason = "general",
}: RelatedEventsWidgetProps) {
  // Filter out current event and limit to 5
  const events = relatedEvents
    .filter((event) => event.event_id !== currentEventId)
    .slice(0, 5);

  if (events.length === 0) {
    return null;
  }

  const reasonLabels = {
    location: "Same Location",
    timeframe: "Around the Same Time",
    general: "Related Events",
  };

  return (
    <div className="space-y-3 rounded-lg border border-gray-700 bg-gray-800/50 p-5">
      <div className="flex items-center gap-2">
        <span className="text-lg">🔗</span>
        <h3 className="text-lg font-bold text-white">{reasonLabels[reason]}</h3>
      </div>

      <div className="space-y-2">
        {events.map((event) => {
          const eventType =
            normalizeEventType(event.event_type ?? null) ??
            detectEventType(event.name);
          const typeConfig = getEventTypeConfig(eventType);
          const eventDate = new Date(event.date);
          const formattedDate = eventDate.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
          });

          return (
            <Link
              key={event.event_id}
              href={`/events/${event.event_id}`}
              className="block rounded-lg border border-gray-700 bg-gray-900/50 p-3 transition-all hover:scale-[1.01] hover:border-gray-600 hover:bg-gray-900/70"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-bold ${typeConfig.badgeClass}`}
                    >
                      {typeConfig.label}
                    </span>
                    {event.status === "upcoming" && (
                      <span className="rounded bg-green-700/30 px-2 py-0.5 text-xs font-medium text-green-400">
                        Upcoming
                      </span>
                    )}
                  </div>
                  <h4 className="line-clamp-2 text-sm font-medium text-white">
                    {event.name}
                  </h4>
                  <div className="mt-1 flex items-center gap-2 text-xs text-gray-400">
                    <span>📅 {formattedDate}</span>
                    {event.location && (
                      <>
                        <span>•</span>
                        <span>📍 {event.location}</span>
                      </>
                    )}
                  </div>
                </div>
                <svg
                  className="h-5 w-5 flex-shrink-0 text-gray-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </div>
            </Link>
          );
        })}
      </div>

      {relatedEvents.length > 5 && (
        <div className="pt-2 text-center text-xs text-gray-500">
          +{relatedEvents.length - 5} more events
        </div>
      )}
    </div>
  );
}
