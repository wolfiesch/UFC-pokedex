import Link from "next/link";
import { differenceInDays, format, parseISO } from "date-fns";
import {
  groupEventsByMonth,
  formatMonthYear,
  getEventTypeConfig,
  detectEventType,
  normalizeEventType,
  type EventType,
} from "@/lib/event-utils";
import { CalendarDays, MapPin } from "lucide-react";

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
    <div className="space-y-16">
      {sortedMonths.map(([monthKey, monthEvents]) => (
        <section key={monthKey} className="snap-start">
          <div className="sticky top-20 z-20 ml-3 inline-flex flex-col rounded-full border border-white/10 bg-white/10 px-6 py-3 text-xs uppercase tracking-[0.35em] text-slate-100 shadow-[0_20px_60px_-40px_rgba(15,23,42,0.9)] backdrop-blur">
            <span className="text-base font-semibold tracking-[0.4em]">{formatMonthYear(monthKey)}</span>
            <span className="text-[0.65rem] text-slate-300/70">{monthEvents.length} {monthEvents.length === 1 ? "event" : "events"}</span>
          </div>

          <div className="mt-8 space-y-10 pl-8">
            {monthEvents.map((event, index) => {
              const eventType = normalizeEventType(event.event_type ?? null) ?? detectEventType(event.name);
              const typeConfig = getEventTypeConfig(eventType);
              const isUpcoming = event.status === "upcoming";
              const eventDate = parseISO(event.date);
              const previous = index > 0 ? parseISO(monthEvents[index - 1].date) : null;
              const dayDelta = previous ? differenceInDays(eventDate, previous) : null;
              const isLeftAligned = index % 2 === 0;

              return (
                <div key={event.event_id} className={`relative flex ${isLeftAligned ? "justify-start" : "justify-end"}`}>
                  <div className="absolute left-[-2.25rem] top-0 flex flex-col items-center">
                    <span className={`h-3 w-3 rounded-full ${isUpcoming ? "bg-emerald-400" : "bg-cyan-400"} shadow-lg`} />
                    <span className="w-px flex-1 bg-gradient-to-b from-white/40 via-white/10 to-transparent" aria-hidden="true" />
                  </div>

                  <Link
                    href={`/events/${event.event_id}`}
                    className={`group flex w-full max-w-xl flex-col gap-4 rounded-[28px] border border-white/10 bg-slate-900/70 p-5 text-slate-100 shadow-[0_30px_80px_-60px_rgba(15,23,42,0.95)] backdrop-blur transition hover:-translate-y-1 hover:border-white/30 ${typeConfig.backdropTexture}`}
                  >
                    <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.3em] text-slate-300/80">
                      <CalendarDays className="h-4 w-4" aria-hidden="true" />
                      <span>{format(eventDate, "MMM d, yyyy")}</span>
                      <span className={`rounded-full px-3 py-1 text-[0.6rem] font-semibold ${typeConfig.badgeClass}`}>
                        {typeConfig.label}
                      </span>
                      {isUpcoming && (
                        <span className="rounded-full border border-emerald-400/60 bg-emerald-400/10 px-3 py-1 text-[0.6rem] font-semibold text-emerald-200">
                          Upcoming
                        </span>
                      )}
                      {dayDelta !== null && dayDelta > 0 && (
                        <span className="rounded-full border border-white/20 bg-white/5 px-3 py-1 text-[0.6rem] text-slate-200">
                          {dayDelta} days after
                        </span>
                      )}
                    </div>

                    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                      <div className="flex-1">
                        <h3 className="text-lg font-bold leading-tight text-white md:text-xl">{event.name}</h3>
                        {event.location && (
                          <p className="mt-1 flex items-center gap-2 text-sm text-slate-200">
                            <MapPin className="h-4 w-4" aria-hidden="true" />
                            <span className="truncate">{event.location}</span>
                          </p>
                        )}
                      </div>
                      <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.3em] text-slate-200 transition group-hover:border-white/40 group-hover:bg-white/20">
                        View card →
                      </span>
                    </div>
                  </Link>
                </div>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
