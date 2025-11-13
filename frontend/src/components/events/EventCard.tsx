import clsx from "clsx";
import Link from "next/link";
import { format, parseISO } from "date-fns";
import {
  getEventTypeConfig,
  detectEventType,
  normalizeEventType,
  type EventType,
} from "@/lib/event-utils";
import {
  ArrowRight,
  CalendarDays,
  Clock3,
  Landmark,
  MapPin,
  Tv,
  Trophy,
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

const EVENT_TYPE_ACCENTS: Record<EventType, { spine: string; glow: string; poster: string }> = {
  ppv: {
    spine: "from-amber-500 via-amber-400 to-amber-600",
    glow: "shadow-[0_0_40px_rgba(245,158,11,0.35)]",
    poster:
      "linear-gradient(135deg, rgba(250,204,21,0.12), rgba(245,158,11,0.05)), url('/textures/octagon-grid.svg')",
  },
  fight_night: {
    spine: "from-rose-500 via-red-500 to-rose-600",
    glow: "shadow-[0_0_35px_rgba(244,63,94,0.28)]",
    poster:
      "linear-gradient(135deg, rgba(244,114,182,0.12), rgba(239,68,68,0.05)), url('/textures/octagon-grid.svg')",
  },
  ufc_on_espn: {
    spine: "from-red-500 via-orange-500 to-yellow-500",
    glow: "shadow-[0_0_35px_rgba(248,113,113,0.28)]",
    poster:
      "linear-gradient(135deg, rgba(248,113,113,0.12), rgba(252,211,77,0.05)), url('/textures/octagon-grid.svg')",
  },
  ufc_on_abc: {
    spine: "from-blue-500 via-sky-400 to-cyan-400",
    glow: "shadow-[0_0_35px_rgba(96,165,250,0.25)]",
    poster:
      "linear-gradient(135deg, rgba(96,165,250,0.12), rgba(56,189,248,0.05)), url('/textures/octagon-grid.svg')",
  },
  tuf_finale: {
    spine: "from-purple-500 via-fuchsia-500 to-purple-600",
    glow: "shadow-[0_0_35px_rgba(168,85,247,0.28)]",
    poster:
      "linear-gradient(135deg, rgba(167,139,250,0.12), rgba(217,70,239,0.05)), url('/textures/octagon-grid.svg')",
  },
  contender_series: {
    spine: "from-emerald-500 via-teal-400 to-emerald-600",
    glow: "shadow-[0_0_35px_rgba(52,211,153,0.28)]",
    poster:
      "linear-gradient(135deg, rgba(16,185,129,0.12), rgba(45,212,191,0.05)), url('/textures/octagon-grid.svg')",
  },
  other: {
    spine: "from-slate-500 via-slate-400 to-slate-500",
    glow: "shadow-[0_0_25px_rgba(148,163,184,0.2)]",
    poster:
      "linear-gradient(135deg, rgba(148,163,184,0.12), rgba(30,41,59,0.08)), url('/textures/octagon-grid.svg')",
  },
};

const NOISE_BACKGROUND =
  "linear-gradient(transparent, transparent), url('/textures/noise.svg')";

function extractHeadliners(name: string): string {
  const colonSplit = name.split(":");
  if (colonSplit.length > 1) {
    return colonSplit.slice(1).join(":").trim();
  }

  const vsMatch = /([A-Za-z\s'.-]+vs\.?\s*[A-Za-z\s'.-]+)/i.exec(name);
  if (vsMatch) {
    return vsMatch[1].replace(/\s+/g, " ").trim();
  }

  return name;
}

export default function EventCard({ event }: EventCardProps) {
  const eventType =
    normalizeEventType(event.event_type ?? null) ?? detectEventType(event.name);
  const typeConfig = getEventTypeConfig(eventType);
  const accent = EVENT_TYPE_ACCENTS[eventType];
  const isUpcoming = event.status === "upcoming";
  const headliners = extractHeadliners(event.name);

  return (
    <Link
      href={`/events/${event.event_id}`}
      className={clsx(
        "group relative overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-6 shadow-[0_18px_45px_rgba(15,23,42,0.45)] backdrop-blur",
        accent.glow,
      )}
    >
      <div className="absolute inset-0 opacity-70 transition group-hover:opacity-90" style={{ backgroundImage: `${accent.poster}, ${NOISE_BACKGROUND}` }} />
      <div className="absolute inset-0 bg-gradient-to-r from-black/70 via-black/40 to-transparent" />
      <div className="relative flex flex-col gap-6 lg:flex-row">
        <div className="relative flex flex-1 flex-col gap-4">
          <div className={`absolute -left-6 top-0 hidden h-full w-2 rounded-full bg-gradient-to-b ${accent.spine} lg:block`} />

          <div className="flex items-center gap-3">
            <span className="inline-flex items-center rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.4em] text-white/80">
              {typeConfig.label}
            </span>
            <span
              className={clsx(
                "inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold uppercase",
                isUpcoming
                  ? "bg-emerald-500/20 text-emerald-200"
                  : "bg-slate-700/60 text-slate-200",
              )}
            >
              <Clock3 className="h-3.5 w-3.5" />
              {isUpcoming ? "Upcoming" : "Completed"}
            </span>
          </div>

          <div>
            <h2 className="text-2xl font-black text-white sm:text-3xl">
              {event.name}
            </h2>
            <p className="mt-2 text-sm uppercase tracking-[0.35em] text-white/50">
              {headliners}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <MetadataBadge
              icon={CalendarDays}
              label="Date"
              value={format(parseISO(event.date), "MMMM d, yyyy")}
            />
            {event.location && (
              <MetadataBadge icon={MapPin} label="Location" value={event.location} />
            )}
            {event.venue && (
              <MetadataBadge icon={Landmark} label="Venue" value={event.venue} />
            )}
            {event.broadcast && (
              <MetadataBadge icon={Tv} label="Broadcast" value={event.broadcast} />
            )}
          </div>

          <div className="mt-auto flex items-center justify-between pt-4">
            <div className="flex items-center gap-3 text-sm text-white/60">
              <Trophy className="h-4 w-4 text-amber-300" />
              <span>See fight card &amp; results</span>
            </div>
            <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-sm font-semibold text-white transition group-hover:bg-white/20">
              See Fight Card
              <ArrowRight className="h-4 w-4" />
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}

interface MetadataBadgeProps {
  icon: typeof CalendarDays;
  label: string;
  value: string;
}

function MetadataBadge({ icon: Icon, label, value }: MetadataBadgeProps) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-black/40 px-3 py-3 text-white/80 shadow-inner">
      <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-white/10">
        <Icon className="h-4 w-4 text-white/70" />
      </span>
      <div>
        <p className="text-xs uppercase tracking-wide text-white/50">{label}</p>
        <p className="text-sm font-semibold text-white">{value}</p>
      </div>
    </div>
  );
}
