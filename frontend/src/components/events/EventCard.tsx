import Link from "next/link";
import { format, parseISO } from "date-fns";
import {
  getEventTypeConfig,
  detectEventType,
  normalizeEventType,
  type EventType,
} from "@/lib/event-utils";
import {
  CalendarDays,
  MapPin,
  Tv,
  Building2,
  ArrowRight,
  Trophy,
  Clock,
} from "lucide-react";

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
  const eventType =
    normalizeEventType(event.event_type ?? null) ?? detectEventType(event.name);
  const typeConfig = getEventTypeConfig(eventType);
  const isUpcoming = event.status === "upcoming";
  const isPPV = eventType === "ppv";
  const eventDate = parseISO(event.date);
  const noiseTexture =
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='60' height='60' viewBox='0 0 60 60'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='60' height='60' filter='url(%23n)' opacity='0.45'/%3E%3C/svg%3E";

  const locationText = event.location ?? "Location TBA";
  const venueText = event.venue ?? "Venue to be announced";

  return (
    <Link
      href={`/events/${event.event_id}`}
      className="group block"
      aria-label={`View details for ${event.name}`}
    >
      <article
        className={`relative overflow-hidden rounded-3xl border border-slate-700/60 ${typeConfig.cardGradient} transition-all duration-300 ${typeConfig.glowShadow} hover:-translate-y-1 hover:border-white/20`}
      >
        <div className="absolute inset-0 opacity-70 mix-blend-screen" style={{
          backgroundImage:
            "radial-gradient(circle at 20% 20%, rgba(255,255,255,0.08), transparent 55%), radial-gradient(circle at 80% 0%, rgba(255,255,255,0.06), transparent 50%), radial-gradient(circle at 50% 80%, rgba(255,255,255,0.05), transparent 60%)",
        }} />
        <div
          className="absolute inset-0 opacity-30 mix-blend-overlay"
          style={{ backgroundImage: `url(${noiseTexture})` }}
          aria-hidden
        />

        <div className="relative flex flex-col lg:flex-row">
          <div className={`hidden lg:block w-2 ${typeConfig.spineGradient}`} aria-hidden />

          <div className="flex-1 p-6 sm:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <span
                    className={`inline-flex items-center gap-1 rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-slate-300/80 ${
                      isPPV ? "bg-amber-500/10 text-amber-200" : ""
                    }`}
                  >
                    {typeConfig.label}
                  </span>
                  <span
                    className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold ${
                      isUpcoming
                        ? "bg-emerald-500/10 text-emerald-300 border border-emerald-400/40"
                        : "bg-slate-700/40 text-slate-200 border border-slate-600/60"
                    }`}
                  >
                    <Clock className="h-3.5 w-3.5" aria-hidden />
                    {isUpcoming ? "Upcoming" : "Completed"}
                  </span>
                </div>

                <div className="space-y-1">
                  <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-white drop-shadow-[0_10px_30px_rgba(0,0,0,0.45)]">
                    {event.name}
                  </h2>
                  <p className="text-sm uppercase tracking-[0.35em] text-slate-400">
                    {format(eventDate, "EEEE, MMMM d yyyy")}
                  </p>
                </div>

                <div className="grid gap-3 text-sm text-slate-300 sm:grid-cols-2">
                  <div className="flex items-center gap-2">
                    <CalendarDays className="h-4 w-4 text-slate-400" aria-hidden />
                    <span>{format(eventDate, "PPpp")}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-slate-400" aria-hidden />
                    <span className="truncate" title={locationText}>
                      {locationText}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-slate-400" aria-hidden />
                    <span className="truncate" title={venueText}>
                      {venueText}
                    </span>
                  </div>
                  {event.broadcast && (
                    <div className="flex items-center gap-2">
                      <Tv className="h-4 w-4 text-slate-400" aria-hidden />
                      <span className="truncate" title={event.broadcast}>
                        {event.broadcast}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex flex-col items-end gap-4 text-right">
                {isPPV && (
                  <span className="inline-flex items-center gap-2 rounded-full border border-amber-400/40 bg-amber-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.25em] text-amber-200">
                    <Trophy className="h-4 w-4" aria-hidden /> PPV Marquee
                  </span>
                )}

                <div className="text-sm text-slate-300">
                  <p className="font-semibold text-slate-200">Feature fights</p>
                  <p className="text-slate-400">
                    Explore full card, bout order, and story beats for this event.
                  </p>
                </div>

                <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium uppercase tracking-[0.2em] text-slate-200">
                  <ArrowRight className="h-4 w-4" aria-hidden /> See Fight Card
                </span>
              </div>
            </div>
          </div>

          <div className="relative h-40 overflow-hidden rounded-b-3xl border-t border-white/5 bg-gradient-to-r from-black/60 via-slate-900/60 to-black/40 sm:h-48 lg:h-auto lg:w-64 lg:rounded-none lg:border-l">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.12),_transparent_60%)]" aria-hidden />
            <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.12)_0%,rgba(255,255,255,0)_55%)] mix-blend-overlay" aria-hidden />
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-center text-xs uppercase tracking-[0.45em] text-slate-300/80">
              <span className="text-base font-medium text-white/80">Immersive Preview</span>
              <span className="text-slate-400">Tap to enter the tale of the tape</span>
            </div>
          </div>
        </div>
      </article>
    </Link>
  );
}
