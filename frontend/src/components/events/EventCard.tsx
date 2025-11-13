import Link from "next/link";
import { format, parseISO } from "date-fns";
import {
  ArrowRight,
  Building2,
  CalendarDays,
  CheckCircle2,
  Clock,
  MapPin,
  Tv,
} from "lucide-react";
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

const EVENT_TYPE_BACKDROPS: Record<EventType | "other", string> = {
  ppv: "https://images.unsplash.com/photo-1509221963642-73a5b9fbf098?auto=format&fit=crop&w=1600&q=80",
  fight_night: "https://images.unsplash.com/photo-1521412644187-c49fa049e84d?auto=format&fit=crop&w=1600&q=80",
  ufc_on_espn: "https://images.unsplash.com/photo-1534159462434-d05e096022a2?auto=format&fit=crop&w=1600&q=80",
  ufc_on_abc: "https://images.unsplash.com/photo-1471295253337-3ceaaedca402?auto=format&fit=crop&w=1600&q=80",
  tuf_finale: "https://images.unsplash.com/photo-1544511916-0148ccdeb877?auto=format&fit=crop&w=1600&q=80",
  contender_series: "https://images.unsplash.com/photo-1544919989-baca9ad34974?auto=format&fit=crop&w=1600&q=80",
  other: "https://images.unsplash.com/photo-1522171989545-939dff55a4c0?auto=format&fit=crop&w=1600&q=80",
};

const EVENT_TYPE_SPINES: Record<EventType | "other", string> = {
  ppv: "from-amber-400 via-orange-500 to-red-600",
  fight_night: "from-slate-400 via-slate-500 to-slate-600",
  ufc_on_espn: "from-red-400 via-rose-500 to-red-600",
  ufc_on_abc: "from-sky-400 via-blue-500 to-blue-600",
  tuf_finale: "from-purple-400 via-fuchsia-500 to-purple-600",
  contender_series: "from-emerald-400 via-teal-500 to-emerald-600",
  other: "from-zinc-400 via-zinc-500 to-zinc-600",
};

export default function EventCard({ event }: EventCardProps) {
  // Use event_type from API or detect from name.
  const normalizedEventType =
    normalizeEventType(event.event_type ?? null) ?? detectEventType(event.name);
  const typeKey = normalizedEventType ?? "other";
  const typeConfig = getEventTypeConfig(normalizedEventType);

  const isUpcoming = event.status === "upcoming";
  const posterImage = EVENT_TYPE_BACKDROPS[typeKey];
  const spineGradient = EVENT_TYPE_SPINES[typeKey];

  const [title, tagline] = event.name.includes(":")
    ? event.name.split(":").map((segment) => segment.trim())
    : [event.name, "Fight card revealed soon"];

  const formattedDate = format(parseISO(event.date), "MMMM d, yyyy");

  return (
    <Link
      href={`/events/${event.event_id}`}
      className="group relative block overflow-hidden rounded-3xl border border-white/10 bg-slate-900/70 shadow-[0_25px_60px_-30px_rgba(15,23,42,1)] transition hover:-translate-y-1 hover:shadow-[0_35px_80px_-30px_rgba(14,116,144,0.45)]"
    >
      <div className="absolute inset-0">
        <div
          className="h-full w-full"
          aria-hidden="true"
          style={{
            backgroundImage: `linear-gradient(135deg, rgba(15,23,42,0.92) 10%, rgba(15,23,42,0.5) 70%, rgba(15,23,42,0.85) 100%), url('${posterImage}')`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />
      </div>
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.12),transparent_55%)] opacity-40 mix-blend-soft-light" aria-hidden="true" />
      <div className="relative grid gap-6 p-6 md:grid-cols-[minmax(0,1fr)_260px]">
        <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur">
          <span
            className={`absolute left-0 top-0 h-full w-1.5 bg-gradient-to-b ${spineGradient}`}
            aria-hidden="true"
          />
          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.25em] text-white/60">
            <span className={`rounded-full px-3 py-1 text-[0.65rem] font-black uppercase tracking-[0.3em] ${typeConfig.badgeClass}`}>
              {typeConfig.label}
            </span>
            <span
              className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.25em] ${
                isUpcoming
                  ? "bg-emerald-500/20 text-emerald-100"
                  : "bg-blue-500/20 text-blue-100"
              }`}
            >
              {isUpcoming ? (
                <Clock className="h-3 w-3" aria-hidden="true" />
              ) : (
                <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
              )}
              {isUpcoming ? "Upcoming" : "Completed"}
            </span>
          </div>

          <div className="mt-5 space-y-3">
            <div>
              <h2 className="text-2xl font-black text-white drop-shadow-sm md:text-3xl">{title}</h2>
              <p className="mt-2 text-sm font-medium uppercase tracking-[0.3em] text-amber-200/80">{tagline}</p>
            </div>

            <div className="grid gap-3 text-sm text-white/80 sm:grid-cols-2">
              <div className="flex items-center gap-2">
                <CalendarDays className="h-4 w-4 text-white/60" aria-hidden="true" />
                <span>{formattedDate}</span>
              </div>
              {event.location && (
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-white/60" aria-hidden="true" />
                  <span className="truncate">{event.location}</span>
                </div>
              )}
              {event.venue && (
                <div className="flex items-center gap-2">
                  <Building2 className="h-4 w-4 text-white/60" aria-hidden="true" />
                  <span className="truncate">{event.venue}</span>
                </div>
              )}
              {event.broadcast && (
                <div className="flex items-center gap-2">
                  <Tv className="h-4 w-4 text-white/60" aria-hidden="true" />
                  <span className="truncate">{event.broadcast}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="flex h-full flex-col justify-between gap-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-5 backdrop-blur">
            <p className="text-xs font-semibold uppercase tracking-[0.35em] text-white/60">Storyline snapshot</p>
            <p className="mt-3 text-sm text-white/80">
              Revisit the rivalries, title stakes, and stylistic clashes defining this event. Dive deeper for full fight-card
              analysis, tale-of-the-tape breakdowns, and broadcast logistics.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur">
            <div className="text-xs uppercase tracking-[0.35em] text-white/60">Enter the card</div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white/90">See Fight Card</span>
              <ArrowRight className="h-4 w-4 text-amber-300 transition group-hover:translate-x-1" aria-hidden="true" />
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
