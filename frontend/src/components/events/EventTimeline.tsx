import Link from "next/link";
import { format, parseISO, differenceInCalendarDays } from "date-fns";
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
    <div className="space-y-12">
      {sortedMonths.map(([monthKey, monthEvents]) => {
        const monthSorted = [...monthEvents].sort(
          (a, b) => parseISO(a.date).getTime() - parseISO(b.date).getTime()
        );

        return (
          <section key={monthKey} className="space-y-6">
            <div className="sticky top-20 z-30 inline-flex min-w-[14rem] items-center gap-3 rounded-full border border-white/20 bg-slate-900/80 px-6 py-3 shadow-[0_20px_60px_-40px_rgba(59,130,246,0.6)] backdrop-blur">
              <span className="text-sm font-semibold uppercase tracking-[0.35em] text-slate-200">
                {formatMonthYear(monthKey)}
              </span>
              <span className="rounded-full bg-slate-800 px-3 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.3em] text-slate-400">
                {monthEvents.length} {monthEvents.length === 1 ? "event" : "events"}
              </span>
            </div>

            <div className="relative grid gap-8 lg:grid-cols-2">
              {monthSorted.map((event, index) => {
                const eventType =
                  normalizeEventType(event.event_type ?? null) ?? detectEventType(event.name);
                const typeConfig = getEventTypeConfig(eventType);
                const isUpcoming = event.status === "upcoming";
                const isPPV = eventType === "ppv";
                const previous = index > 0 ? monthSorted[index - 1] : null;
                const daysBetween = previous
                  ? differenceInCalendarDays(parseISO(event.date), parseISO(previous.date))
                  : null;

                return (
                  <div
                    key={event.event_id}
                    className="relative flex scroll-mt-24 scroll-smooth flex-col gap-3 rounded-3xl border border-white/10 bg-slate-950/70 p-5 shadow-[0_30px_60px_-50px_rgba(15,23,42,0.85)] backdrop-blur-lg"
                    style={{ scrollSnapAlign: "start" }}
                  >
                    <div className="absolute -left-6 top-1/2 hidden h-20 w-px -translate-y-1/2 bg-gradient-to-b from-transparent via-white/30 to-transparent lg:block" />
                    <div className="flex items-center justify-between">
                      <div className="inline-flex items-center gap-3 rounded-full border border-white/20 bg-white/5 px-4 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-slate-200">
                        {format(parseISO(event.date), "MMM d")}
                        <span className={`rounded-full px-2 py-0.5 text-[0.6rem] font-bold ${typeConfig.badgeClass}`}>
                          {typeConfig.label}
                        </span>
                        {isUpcoming && (
                          <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[0.6rem] font-semibold text-emerald-200">
                            Upcoming
                          </span>
                        )}
                      </div>
                      {daysBetween && (
                        <span className="rounded-full bg-white/5 px-3 py-1 text-[0.6rem] font-semibold uppercase tracking-[0.3em] text-slate-400">
                          +{daysBetween} days
                        </span>
                      )}
                    </div>

                    <Link
                      href={`/events/${event.event_id}`}
                      className="group grid gap-4 lg:grid-cols-[0.25fr_1fr]"
                    >
                      <div className="relative aspect-[3/4] overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-white/10 via-transparent to-white/5">
                        <div
                          className="absolute inset-0 opacity-60 transition duration-500 group-hover:opacity-90"
                          style={{
                            backgroundImage: `linear-gradient(135deg, rgba(15,23,42,0.8), rgba(15,23,42,0.3)), url('https://images.unsplash.com/photo-1533560904424-4b9d0f06e5d4?auto=format&fit=crop&w=700&q=80')`,
                            backgroundSize: "cover",
                            backgroundPosition: "center",
                          }}
                        />
                        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-slate-950 via-slate-950/60 to-transparent p-3 text-[0.65rem] font-semibold uppercase tracking-[0.3em] text-white">
                          {eventType === "ppv" ? "PPV Poster" : "Event Poster"}
                        </div>
                      </div>

                      <div className="flex flex-col justify-between gap-4">
                        <div>
                          <h3 className={`text-lg font-black leading-tight ${isPPV ? "text-amber-200" : "text-white"}`}>
                            {event.name}
                          </h3>
                          {event.location && (
                            <p className="text-sm text-slate-300">{event.location}</p>
                          )}
                        </div>
                        <div className="flex items-center justify-between text-[0.7rem] uppercase tracking-[0.3em] text-slate-400">
                          <span>Swipe for card</span>
                          <span className="inline-flex items-center gap-2 text-sky-300 transition group-hover:translate-x-1">
                            Explore
                          </span>
                        </div>
                      </div>
                    </Link>
                  </div>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
