import Link from "next/link";
import { format, parseISO } from "date-fns";
import { getEventTypeConfig, detectEventType, type EventType } from "@/lib/event-utils";

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
  const eventType = event.event_type || detectEventType(event.name);
  const typeConfig = getEventTypeConfig(eventType);

  const isUpcoming = event.status === "upcoming";
  const isPPV = eventType === "ppv";

  return (
    <Link
      href={`/events/${event.event_id}`}
      className={`block p-6 rounded-lg transition-all duration-200 border hover:scale-[1.01] hover:shadow-lg ${typeConfig.bgClass} ${
        isPPV ? "shadow-amber-900/20" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Event Name */}
          <div className="flex items-start gap-3 mb-3">
            <h2 className={`text-xl font-bold ${isPPV ? "text-amber-200" : "text-white"} line-clamp-2`}>
              {event.name}
            </h2>
          </div>

          {/* Event Metadata */}
          <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-gray-400">📅</span>
              <span className={isPPV ? "text-amber-200 font-medium" : "text-gray-300"}>
                {format(parseISO(event.date), "MMMM d, yyyy")}
              </span>
            </div>

            {event.location && (
              <div className="flex items-center gap-2">
                <span className="text-gray-400">📍</span>
                <span className={isPPV ? "text-amber-200" : "text-gray-300"}>{event.location}</span>
              </div>
            )}

            {event.venue && (
              <div className="flex items-center gap-2">
                <span className="text-gray-400">🏟️</span>
                <span className={`truncate ${isPPV ? "text-amber-200" : "text-gray-300"}`}>{event.venue}</span>
              </div>
            )}

            {event.broadcast && (
              <div className="flex items-center gap-2">
                <span className="text-gray-400">📺</span>
                <span className={isPPV ? "text-amber-200" : "text-gray-300"}>{event.broadcast}</span>
              </div>
            )}
          </div>
        </div>

        {/* Status and Type Badges */}
        <div className="flex flex-col gap-2 items-end flex-shrink-0">
          <span
            className={`px-3 py-1 rounded-full text-xs font-medium ${
              isUpcoming ? "bg-green-900 text-green-300" : "bg-gray-700 text-gray-300"
            }`}
          >
            {isUpcoming ? "Upcoming" : "Completed"}
          </span>

          {/* Event Type Badge */}
          <span className={`px-3 py-1 rounded-full text-xs font-bold ${typeConfig.badgeClass}`}>
            {typeConfig.label}
          </span>
        </div>
      </div>

      {/* PPV Special Indicator */}
      {isPPV && (
        <div className="mt-4 pt-4 border-t border-amber-600/40">
          <div className="flex items-center gap-2 text-xs">
            <span className="font-bold text-amber-300">⭐ Pay-Per-View Event</span>
          </div>
        </div>
      )}
    </Link>
  );
}
