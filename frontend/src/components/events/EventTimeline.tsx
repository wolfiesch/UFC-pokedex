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
  const sortedMonths = Array.from(groupedEvents.entries()).sort((a, b) =>
    b[0].localeCompare(a[0]),
  );

  if (events.length === 0) {
    return (
      <div className="py-12 text-center text-gray-400">No events found.</div>
    );
  }

  return (
    <div className="space-y-8">
      {sortedMonths.map(([monthKey, monthEvents]) => (
        <div key={monthKey}>
          {/* Month Header */}
          <div className="sticky top-0 z-10 mb-4 rounded-r-lg border-l-4 border-blue-600 bg-gradient-to-r from-gray-900 to-gray-800 py-2 pl-4 shadow-lg">
            <h2 className="text-2xl font-bold text-white">
              {formatMonthYear(monthKey)}
            </h2>
            <p className="text-sm text-gray-400">
              {monthEvents.length}{" "}
              {monthEvents.length === 1 ? "event" : "events"}
            </p>
          </div>

          {/* Events for this month */}
          <div className="ml-8 space-y-3">
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
                  className="group block"
                >
                  <div className="flex items-start gap-4">
                    {/* Timeline connector */}
                    <div className="flex flex-shrink-0 flex-col items-center">
                      <div
                        className={`h-3 w-3 rounded-full ${isPPV ? "bg-amber-400" : "bg-blue-500"} shadow-lg transition-transform group-hover:scale-125`}
                      />
                      <div className="mt-1 h-full w-0.5 bg-gray-700" />
                    </div>

                    {/* Event content */}
                    <div
                      className={`flex-1 rounded-lg border p-4 transition-all duration-200 ${typeConfig.bgClass} group-hover:scale-[1.01] group-hover:shadow-lg`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0 flex-1">
                          <div className="mb-1 flex items-center gap-2">
                            <span
                              className={`text-xs ${isPPV ? "font-medium text-amber-300" : "text-gray-400"}`}
                            >
                              {format(parseISO(event.date), "MMM d")}
                            </span>
                            <span
                              className={`rounded-full px-2 py-0.5 text-xs ${typeConfig.badgeClass}`}
                            >
                              {typeConfig.label}
                            </span>
                            {isUpcoming && (
                              <span className="rounded-full bg-green-700 px-2 py-0.5 text-xs font-semibold text-white">
                                Upcoming
                              </span>
                            )}
                          </div>
                          <h3
                            className={`font-bold ${isPPV ? "text-lg text-amber-200" : "text-white"} mb-1 line-clamp-1`}
                          >
                            {event.name}
                          </h3>
                          {event.location && (
                            <p
                              className={`flex items-center gap-1 text-sm ${isPPV ? "text-amber-200" : "text-gray-300"}`}
                            >
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
