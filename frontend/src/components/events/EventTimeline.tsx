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
import { CalendarDays, Clock3, MapPin, Sparkles } from "lucide-react";

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
        <section key={monthKey} className="relative">
          <div className="sticky top-28 z-20 mx-auto mb-10 flex w-fit items-center gap-3 rounded-full border border-white/15 bg-slate-950/90 px-6 py-3 text-xs uppercase tracking-[0.35em] text-slate-200 shadow-xl shadow-black/40 backdrop-blur">
            <Sparkles className="h-4 w-4 text-sky-300" aria-hidden />
            {formatMonthYear(monthKey)} · {monthEvents.length} {monthEvents.length === 1 ? "event" : "events"}
          </div>

          <div className="relative mx-auto flex max-w-5xl flex-col gap-10 overflow-hidden rounded-[3rem] border border-white/10 bg-slate-950/70 p-8 shadow-[0_30px_120px_rgba(15,23,42,0.55)] backdrop-blur-xl">
            <div className="absolute inset-y-0 left-1/2 w-px bg-gradient-to-b from-transparent via-slate-700/60 to-transparent" aria-hidden />

            <div className="grid gap-16 snap-y snap-mandatory">
              {monthEvents.map((event, index) => {
                const eventType =
                  normalizeEventType(event.event_type ?? null) ?? detectEventType(event.name);
                const typeConfig = getEventTypeConfig(eventType);
                const isUpcoming = event.status === "upcoming";
                const isLeft = index % 2 === 0;
                const previousEvent = monthEvents[index - 1];
                const daysBetween = previousEvent
                  ? Math.abs(
                      differenceInCalendarDays(
                        parseISO(event.date),
                        parseISO(previousEvent.date)
                      )
                    )
                  : null;

                return (
                  <article
                    key={event.event_id}
                    className={`group relative grid scroll-mt-36 snap-start items-center gap-6 lg:grid-cols-[1fr_minmax(0,360px)] ${
                      isLeft ? "lg:text-right" : ""
                    }`}
                  >
                    <div className={`flex flex-col gap-3 ${isLeft ? "lg:items-end" : ""}`}>
                      <div className="flex items-center gap-2 text-xs uppercase tracking-[0.3em] text-slate-400">
                        <CalendarDays className="h-4 w-4" aria-hidden />
                        {format(parseISO(event.date), "EEE MMM d" )}
                        {daysBetween !== null && (
                          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-[0.35em] text-slate-300">
                            <Clock3 className="h-3 w-3" aria-hidden />
                            +{daysBetween} days
                          </span>
                        )}
                      </div>
                      <h3 className={`text-xl font-semibold text-white ${isLeft ? "lg:ml-auto" : ""}`}>
                        {event.name}
                      </h3>
                      <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${
                        isUpcoming
                          ? "border-emerald-400/60 bg-emerald-500/10 text-emerald-100"
                          : "border-white/10 bg-white/5 text-slate-200"
                      } ${isLeft ? "lg:ml-auto" : ""}`}>
                        {typeConfig.label}
                      </div>
                      {event.location && (
                        <p className={`flex items-center gap-2 text-sm text-slate-300 ${isLeft ? "lg:justify-end" : ""}`}>
                          <MapPin className="h-4 w-4 text-slate-400" aria-hidden />
                          <span className="truncate">{event.location}</span>
                        </p>
                      )}
                      <Link
                        href={`/events/${event.event_id}`}
                        className={`inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.3em] text-sky-200 transition-all hover:text-sky-100 ${
                          isLeft ? "lg:ml-auto" : ""
                        }`}
                      >
                        View fight card →
                      </Link>
                    </div>

                    <div className={`relative flex items-center ${isLeft ? "lg:justify-start" : "lg:justify-end"}`}>
                      <div className={`relative w-full max-w-md overflow-hidden rounded-3xl border border-white/10 ${typeConfig.cardGradient} p-6 shadow-lg shadow-black/30 transition-transform duration-300 group-hover:scale-[1.02]`}>
                        <div className="absolute inset-0 opacity-30" style={{
                          backgroundImage:
                            "radial-gradient(circle at 20% 20%, rgba(255,255,255,0.08), transparent 55%), radial-gradient(circle at 80% 30%, rgba(255,255,255,0.1), transparent 60%)",
                        }} aria-hidden />
                        <div className="relative space-y-3 text-sm text-slate-200">
                          <p className="text-xs uppercase tracking-[0.35em] text-slate-400">
                            Tale of the tape preview
                          </p>
                          <p>
                            {event.venue ? `Hosted at ${event.venue}` : "Venue TBA"}
                          </p>
                          {event.broadcast && <p>Broadcast: {event.broadcast}</p>}
                          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-[0.35em] text-slate-200">
                            <Sparkles className="h-3 w-3 text-sky-300" aria-hidden />
                            {isUpcoming ? "Upcoming" : "Replay"}
                          </div>
                        </div>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        </section>
      ))}
    </div>
  );
}
