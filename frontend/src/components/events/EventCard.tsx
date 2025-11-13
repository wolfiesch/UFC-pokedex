import Link from "next/link";
import { format, parseISO } from "date-fns";
import {
  getEventTypeConfig,
  detectEventType,
  normalizeEventType,
  type EventType,
} from "@/lib/event-utils";
import {
  ArrowUpRight,
  CalendarDays,
  MapPin,
  Radio,
  Tv2,
  VenetianMask,
} from "lucide-react";

const eventTypeArtwork: Record<EventType, string> = {
  ppv: "https://images.unsplash.com/photo-1571008887538-b36bb32f4571?auto=format&fit=crop&w=1600&q=80",
  fight_night: "https://images.unsplash.com/photo-1521410132144-1a1e55e26f58?auto=format&fit=crop&w=1600&q=80",
  ufc_on_espn: "https://images.unsplash.com/photo-1546519638-68e109498ffc?auto=format&fit=crop&w=1600&q=80",
  ufc_on_abc: "https://images.unsplash.com/photo-1471295253337-3ceaaedca402?auto=format&fit=crop&w=1600&q=80",
  tuf_finale: "https://images.unsplash.com/photo-1525954677600-06e3f1c41c08?auto=format&fit=crop&w=1600&q=80",
  contender_series: "https://images.unsplash.com/photo-1533560904424-4b9d0f06e5d4?auto=format&fit=crop&w=1600&q=80",
  other: "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=1600&q=80",
};

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
  const heroArtwork = eventTypeArtwork[eventType] ?? eventTypeArtwork.other;
  const [branding, subtitle] = event.name.split(":");
  const headliner = subtitle ? subtitle.trim() : undefined;

  return (
    <Link
      href={`/events/${event.event_id}`}
      className="group relative block overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-slate-900/80 to-slate-950/80 p-6 shadow-[0_40px_80px_-60px_rgba(15,23,42,0.7)] transition-transform duration-500 hover:-translate-y-1 hover:shadow-[0_50px_90px_-60px_rgba(59,130,246,0.45)]"
    >
      {/* Cinematic background artwork */}
      <div
        className="pointer-events-none absolute inset-0 opacity-70 transition duration-500 group-hover:opacity-90"
        style={{
          backgroundImage: `linear-gradient(135deg, rgba(15,23,42,0.85), rgba(15,23,42,0.45)), url(${heroArtwork})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(148,163,184,0.25),_transparent_60%)] mix-blend-screen opacity-60" />
      <div className="pointer-events-none absolute -inset-y-20 right-0 w-1/2 rotate-12 bg-gradient-to-tr from-transparent via-white/10 to-transparent opacity-40 blur-3xl" />

      {/* Event type spine */}
      <div className={`absolute inset-y-0 left-0 w-1.5 ${typeConfig.badgeClass} opacity-90`} aria-hidden />

      <div className="relative flex flex-col gap-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex flex-1 flex-col gap-3">
            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.3em] text-slate-300/70">
              <VenetianMask className="h-4 w-4 text-slate-200/80" aria-hidden />
              <span>{branding?.trim() ?? "UFC EVENT"}</span>
            </div>

            <h2 className={`text-balance text-2xl font-black leading-tight text-white sm:text-3xl lg:text-4xl ${isPPV ? "drop-shadow-[0_4px_16px_rgba(251,191,36,0.45)]" : ""}`}>
              {event.name}
            </h2>

            {headliner && (
              <p className="max-w-xl text-base font-semibold text-slate-100/90">
                {headliner}
              </p>
            )}

            <div className="flex flex-wrap items-center gap-4 text-sm text-slate-200/80">
              <span className="inline-flex items-center gap-2">
                <CalendarDays className="h-4 w-4" aria-hidden />
                {format(parseISO(event.date), "MMMM d, yyyy")}
              </span>

              {event.location && (
                <span className="inline-flex items-center gap-2">
                  <MapPin className="h-4 w-4" aria-hidden />
                  <span className="truncate max-w-[14rem]">{event.location}</span>
                </span>
              )}

              {event.venue && (
                <span className="inline-flex items-center gap-2">
                  <Radio className="h-4 w-4" aria-hidden />
                  <span className="truncate max-w-[14rem]">{event.venue}</span>
                </span>
              )}

              {event.broadcast && (
                <span className="inline-flex items-center gap-2">
                  <Tv2 className="h-4 w-4" aria-hidden />
                  {event.broadcast}
                </span>
              )}
            </div>
          </div>

          <div className="flex flex-col items-end gap-3 text-right">
            <span
              className={`inline-flex items-center gap-2 rounded-full border px-4 py-1 text-xs font-semibold tracking-wide backdrop-blur-sm transition ${
                isUpcoming
                  ? "border-emerald-400/50 bg-emerald-500/10 text-emerald-200"
                  : "border-slate-200/30 bg-slate-200/5 text-slate-200/80"
              }`}
            >
              {isUpcoming ? "Upcoming" : "Completed"}
            </span>

            <span
              className={`inline-flex items-center gap-2 rounded-full px-4 py-1 text-xs font-bold uppercase tracking-[0.2em] text-white shadow-inner ${typeConfig.badgeClass}`}
            >
              {typeConfig.label}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-100/90 backdrop-blur">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full border border-white/20 bg-gradient-to-br from-white/40 to-transparent shadow-inner" />
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-300/70">Fight Card</p>
              <p className="font-semibold">Dive into matchups, stats, and story beats</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm font-semibold text-sky-300 transition group-hover:text-sky-200">
            <span>See Fight Card</span>
            <ArrowUpRight className="h-4 w-4" aria-hidden />
          </div>
        </div>

        {isPPV && (
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.25em] text-amber-200/90">
            <span className="h-px w-6 bg-amber-400/60" aria-hidden />
            Premier Pay-Per-View Spectacle
          </div>
        )}
      </div>
    </Link>
  );
}
