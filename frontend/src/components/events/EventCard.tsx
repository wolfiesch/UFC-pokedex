import Link from "next/link";
import { format, parseISO } from "date-fns";
import {
  getEventTypeConfig,
  detectEventType,
  normalizeEventType,
  type EventType,
} from "@/lib/event-utils";

interface EventCardProps {
  event: {
    event_id: string;
    name: string;
    date: string;
    location: string | null;
    status: string;
    venue?: string | null;
    broadcast?: string | null;
    event_type?: EventType | null;
  };
}

export default function EventCard({ event }: EventCardProps) {
  // Use event_type from API or detect from name
  const eventType =
    normalizeEventType(event.event_type ?? null) ?? detectEventType(event.name);
  const typeConfig = getEventTypeConfig(eventType);

  const isUpcoming = event.status === "upcoming";
  const isPPV = eventType === "ppv";

  return (
    <Link
      href={`/events/${event.event_id}`}
      className={`block rounded-lg border p-6 transition-all duration-200 hover:scale-[1.01] hover:shadow-lg ${typeConfig.bgClass} ${
        isPPV ? "shadow-amber-900/20" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          {/* Event Name */}
          <div className="mb-3 flex items-start gap-3">
            <h2
              className={`text-xl font-bold ${isPPV ? "text-amber-200" : "text-white"} line-clamp-2`}
            >
              {event.name}
            </h2>
          </div>

          {/* Event Metadata */}
          <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-gray-400">📅</span>
              <span
                className={
                  isPPV ? "font-medium text-amber-200" : "text-gray-300"
                }
              >
                {format(parseISO(event.date), "MMMM d, yyyy")}
              </span>
            </div>

            {event.location && (
              <div className="flex items-center gap-2">
                <span className="text-gray-400">📍</span>
                <span className={isPPV ? "text-amber-200" : "text-gray-300"}>
                  {event.location}
                </span>
              </div>
            )}

            {event.venue && (
              <div className="flex items-center gap-2">
                <span className="text-gray-400">🏟️</span>
                <span
                  className={`truncate ${isPPV ? "text-amber-200" : "text-gray-300"}`}
                >
                  {event.venue}
                </span>
              </div>
            )}

            {event.broadcast && (
              <div className="flex items-center gap-2">
                <span className="text-gray-400">📺</span>
                <span className={isPPV ? "text-amber-200" : "text-gray-300"}>
                  {event.broadcast}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Status and Type Badges */}
        <div className="flex flex-shrink-0 flex-col items-end gap-2">
          <span
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              isUpcoming
                ? "bg-green-900 text-green-300"
                : "bg-gray-700 text-gray-300"
            }`}
          >
            {isUpcoming ? "Upcoming" : "Completed"}
          </span>

          {/* Event Type Badge */}
          <span
            className={`rounded-full px-3 py-1 text-xs font-bold ${typeConfig.badgeClass}`}
          >
            {typeConfig.label}
          </span>
        </div>
      </div>

      {/* PPV Special Indicator */}
      {isPPV && (
        <div className="mt-4 border-t border-amber-600/40 pt-4">
          <div className="flex items-center gap-2 text-xs">
            <span className="font-bold text-amber-300">
              ⭐ Pay-Per-View Event
            </span>
          </div>
        </div>
      )}
    </Link>
  );
}
