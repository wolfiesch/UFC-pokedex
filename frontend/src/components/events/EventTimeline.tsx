import Link from "next/link";
import { format, parseISO } from "date-fns";
import {
  groupEventsByMonth,
  formatMonthYear,
  getEventTypeConfig,
  detectEventType,
  normalizeEventType,
  type EventType,
} from "@/lib/event-utils";

interface Event {
  event_id: string;
  name: string;
  date: string;
  location: string | null;
  status: string;
  venue?: string | null;
  event_type?: EventType | null;
}

interface EventTimelineProps {
  events: Event[];
}

export default function EventTimeline({ events }: EventTimelineProps) {
  const groupedEvents = groupEventsByMonth(events);

  // Convert to array and sort by month (descending)
  const sortedMonths = Array.from(groupedEvents.entries()).sort((a, b) => b[0].localeCompare(a[0]));

  if (events.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        No events found.
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {sortedMonths.map(([monthKey, monthEvents]) => (
        <div key={monthKey}>
          {/* Month Header */}
          <div className="sticky top-0 z-10 bg-gradient-to-r from-gray-900 to-gray-800 border-l-4 border-blue-600 pl-4 py-2 mb-4 rounded-r-lg shadow-lg">
            <h2 className="text-2xl font-bold text-white">{formatMonthYear(monthKey)}</h2>
            <p className="text-sm text-gray-400">{monthEvents.length} {monthEvents.length === 1 ? "event" : "events"}</p>
          </div>

          {/* Events for this month */}
          <div className="space-y-3 ml-8">
            {monthEvents.map((event) => {
              const eventType =
                normalizeEventType(event.event_type ?? null) ??
                detectEventType(event.name);
              const typeConfig = getEventTypeConfig(eventType);
              const isUpcoming = event.status === "upcoming";
              const isPPV = eventType === "ppv";

              return (
                <Link
                  key={event.event_id}
                  href={`/events/${event.event_id}`}
                  className="block group"
                >
                  <div className="flex items-start gap-4">
                    {/* Timeline connector */}
                    <div className="flex-shrink-0 flex flex-col items-center">
                      <div className={`w-3 h-3 rounded-full ${isPPV ? "bg-amber-400" : "bg-blue-500"} group-hover:scale-125 transition-transform shadow-lg`} />
                      <div className="w-0.5 h-full bg-gray-700 mt-1" />
                    </div>

                    {/* Event content */}
                    <div className={`flex-1 p-4 rounded-lg border transition-all duration-200 ${typeConfig.bgClass} group-hover:scale-[1.01] group-hover:shadow-lg`}>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-xs ${isPPV ? "text-amber-300 font-medium" : "text-gray-400"}`}>
                              {format(parseISO(event.date), "MMM d")}
                            </span>
                            <span className={`px-2 py-0.5 rounded-full text-xs ${typeConfig.badgeClass}`}>
                              {typeConfig.label}
                            </span>
                            {isUpcoming && (
                              <span className="px-2 py-0.5 bg-green-700 text-white rounded-full text-xs font-semibold">
                                Upcoming
                              </span>
                            )}
                          </div>
                          <h3 className={`font-bold ${isPPV ? "text-amber-200 text-lg" : "text-white"} line-clamp-1 mb-1`}>
                            {event.name}
                          </h3>
                          {event.location && (
                            <p className={`text-sm flex items-center gap-1 ${isPPV ? "text-amber-200" : "text-gray-300"}`}>
                              <span className="text-gray-400">📍</span>
                              <span className="truncate">{event.location}</span>
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
