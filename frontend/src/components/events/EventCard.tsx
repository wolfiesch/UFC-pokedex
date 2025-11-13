import Link from "next/link";
import { format, parseISO } from "date-fns";
import {
  getEventTypeConfig,
  detectEventType,
  normalizeEventType,
  type EventType,
} from "@/lib/event-utils";
import { CalendarDays, MapPin, PlayCircle, Tv, Building2, ArrowRight } from "lucide-react";

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

  const eventDate = parseISO(event.date);
  const readableDate = format(eventDate, "MMMM d, yyyy");

  // Attempt to split the event name into promotion + headliners for storytelling layout.
  const [promotion, headlinerSegment] = event.name.split(":");
  const headliners = headlinerSegment?.trim() ?? "";

  const headlinerParts = headliners
    .split("vs")
    .map((part) => part.trim())
    .filter(Boolean);

  const locationSummary = event.location?.split(",").slice(-2).join(", ") ?? null;

  const posterSeed = Math.abs(event.event_id.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0)) % 5;
  const posterTextures = [
    "bg-[url('https://images.unsplash.com/photo-1517649763962-0c623066013b?auto=format&fit=crop&w=800&q=80')]",
    "bg-[url('https://images.unsplash.com/photo-1534367610401-9f5ed68180aa?auto=format&fit=crop&w=800&q=80')]",
    "bg-[url('https://images.unsplash.com/photo-1508261303786-0a0d0c1f4a80?auto=format&fit=crop&w=800&q=80')]",
    "bg-[url('https://images.unsplash.com/photo-1489515217757-5fd1be406fef?auto=format&fit=crop&w=800&q=80')]",
    "bg-[url('https://images.unsplash.com/photo-1519677100203-a0e668c92439?auto=format&fit=crop&w=800&q=80')]",
  ];

  return (
    <Link
      href={`/events/${event.event_id}`}
      className={`group relative flex flex-col overflow-hidden rounded-3xl border border-white/10 bg-slate-900/50 p-6 transition-all duration-300 hover:-translate-y-1 hover:border-white/20 hover:shadow-[0_45px_80px_-40px_rgba(15,23,42,0.9)] ${typeConfig.backdropTexture}`}
    >
      <div className="absolute inset-0 opacity-40 transition duration-500 group-hover:opacity-60">
        <div className={`absolute inset-0 ${posterTextures[posterSeed]} bg-cover bg-center blur-sm`} />
        <div className="absolute inset-0 bg-gradient-to-br from-black/70 via-black/40 to-black/90" />
      </div>
      <div className={`absolute -left-12 top-0 h-full w-24 skew-x-[-12deg] opacity-60 ${typeConfig.spineClass}`} aria-hidden="true" />
      <div className="relative z-10 grid grid-cols-1 gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="flex flex-col gap-5">
          <div className="flex items-center justify-between">
            <span className={`rounded-full px-3 py-1 text-xs font-semibold tracking-wide text-white shadow ${typeConfig.badgeClass}`}>
              {typeConfig.label}
            </span>
            <span
              className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${
                isUpcoming ? "bg-emerald-500/10 text-emerald-200" : "bg-slate-700/60 text-slate-200"
              }`}
            >
              <PlayCircle className="h-3.5 w-3.5" aria-hidden="true" />
              {isUpcoming ? "Upcoming" : "Completed"}
            </span>
          </div>

          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-slate-300/70">{promotion?.trim() ?? "UFC"}</p>
            <h2 className="mt-2 text-3xl font-extrabold text-white drop-shadow-sm sm:text-4xl">
              {headliners || event.name}
            </h2>
            {headlinerParts.length >= 2 && (
              <p className="mt-3 text-sm font-medium uppercase tracking-widest text-slate-200/80">
                {headlinerParts.join(" • ")}
              </p>
            )}
          </div>

          <div className="grid grid-cols-1 gap-3 text-sm text-slate-200 sm:grid-cols-2">
            <div className="flex items-center gap-2 rounded-2xl bg-white/5 px-3 py-2">
              <CalendarDays className="h-4 w-4 text-cyan-300" aria-hidden="true" />
              <span className="font-medium">{readableDate}</span>
            </div>
            {locationSummary && (
              <div className="flex items-center gap-2 rounded-2xl bg-white/5 px-3 py-2">
                <MapPin className="h-4 w-4 text-rose-300" aria-hidden="true" />
                <span className="truncate">{locationSummary}</span>
              </div>
            )}
            {event.venue && (
              <div className="flex items-center gap-2 rounded-2xl bg-white/5 px-3 py-2">
                <Building2 className="h-4 w-4 text-amber-300" aria-hidden="true" />
                <span className="truncate">{event.venue}</span>
              </div>
            )}
            {event.broadcast && (
              <div className="flex items-center gap-2 rounded-2xl bg-white/5 px-3 py-2">
                <Tv className="h-4 w-4 text-indigo-300" aria-hidden="true" />
                <span className="truncate">{event.broadcast}</span>
              </div>
            )}
          </div>
        </div>

        <div className="flex flex-col justify-between gap-4 rounded-3xl border border-white/10 bg-white/5 p-5 backdrop-blur">
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-200/70">Storyline</p>
            <p className="text-sm text-slate-100/90">
              {isPPV
                ? "Premier card with global spotlights and championship stakes. Dive into the narratives before the fighters walk."
                : "Stacked lineup packed with prospects and veterans. Explore tales behind every matchup."}
            </p>
          </div>
          <div className="flex items-center justify-between text-xs text-slate-200">
            <span className="uppercase tracking-[0.25em] text-slate-200/70">Dive Deeper</span>
            <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 font-semibold text-slate-50 transition group-hover:bg-white/20">
              See Fight Card
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}
