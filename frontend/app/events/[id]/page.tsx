"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import clsx from "clsx";
import {
  differenceInDays,
  differenceInHours,
  differenceInMinutes,
  format,
  isAfter,
  parseISO,
} from "date-fns";
import { groupFightsBySection } from "@/lib/fight-utils";
import { detectEventType, getEventTypeConfig, normalizeEventType } from "@/lib/event-utils";
import EventStatsPanel from "@/components/events/EventStatsPanel";
import FightCardSection from "@/components/events/FightCardSection";
import RelatedEventsWidget from "@/components/events/RelatedEventsWidget";
import {
  ArrowLeft,
  CalendarDays,
  Clock,
  Globe2,
  Landmark,
  MapPin,
  ShieldCheck,
  Sparkles,
  Tv,
} from "lucide-react";

interface Fight {
  fight_id: string;
  fighter_1_id: string;
  fighter_1_name: string;
  fighter_2_id: string | null;
  fighter_2_name: string;
  weight_class: string | null;
  result: string | null;
  method: string | null;
  round: number | null;
  time: string | null;
}

interface EventDetail {
  event_id: string;
  name: string;
  date: string;
  location: string;
  status: string;
  venue?: string | null;
  broadcast?: string | null;
  promotion: string;
  ufcstats_url: string;
  fight_card: Fight[];
  event_type?: string | null;
}

interface EventListItem {
  event_id: string;
  name: string;
  date: string;
  location: string | null;
  status: string;
  event_type?: string | null;
}

export default function EventDetailPage() {
  const params = useParams();
  const eventId = params?.id as string;
  const [event, setEvent] = useState<EventDetail | null>(null);
  const [relatedEvents, setRelatedEvents] = useState<EventListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchEventDetail() {
      if (!eventId) return;

      setLoading(true);
      setError(null);

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

        // Fetch event details
        const response = await fetch(`${apiUrl}/events/${eventId}`, {
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch event: ${response.statusText}`);
        }

        const data = await response.json();
        setEvent(data);

        // Fetch related events from same location
        if (data.location) {
          try {
            const relatedResponse = await fetch(
              `${apiUrl}/events/search/?location=${encodeURIComponent(data.location)}&limit=6`,
              { cache: "no-store" }
            );
            if (relatedResponse.ok) {
              const relatedData = await relatedResponse.json();
              setRelatedEvents(relatedData.events || []);
            }
          } catch (err) {
            console.error("Error fetching related events:", err);
            // Non-critical error, continue anyway
          }
        }
      } catch (err) {
        console.error("Error fetching event:", err);
        setError(err instanceof Error ? err.message : "Failed to load event");
      } finally {
        setLoading(false);
      }
    }

    fetchEventDetail();
  }, [eventId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading event...</div>
      </div>
    );
  }

  if (error || !event) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-500 mb-4">Error</h1>
          <p className="text-gray-400">{error || "Event not found"}</p>
          <Link href="/events" className="mt-4 inline-block text-blue-500 hover:underline">
            ← Back to Events
          </Link>
        </div>
      </div>
    );
  }

  // Detect event type and get config
  const normalizedEventType =
    normalizeEventType(event.event_type) ?? detectEventType(event.name);
  const typeConfig = getEventTypeConfig(normalizedEventType);
  const isPPV = normalizedEventType === "ppv";

  const eventDate = parseISO(event.date);
  const now = new Date();
  const upcoming = isAfter(eventDate, now);
  const daysRemaining = Math.max(differenceInDays(eventDate, now), 0);
  const hoursRemaining = Math.max(differenceInHours(eventDate, now) - daysRemaining * 24, 0);
  const minutesRemaining = Math.max(
    differenceInMinutes(eventDate, now) - differenceInHours(eventDate, now) * 60,
    0,
  );
  const countdownLabel = upcoming
    ? `${daysRemaining}d ${hoursRemaining}h ${minutesRemaining}m`
    : "Completed";

  const heroAccents: Record<string, { border: string; glow: string; beam: string }> = {
    ppv: {
      border: "border-amber-500/40",
      glow: "from-amber-500/40 via-amber-400/20 to-transparent",
      beam: "rgba(251,191,36,0.2)",
    },
    fight_night: {
      border: "border-rose-500/30",
      glow: "from-rose-500/40 via-rose-400/20 to-transparent",
      beam: "rgba(244,114,182,0.22)",
    },
    ufc_on_espn: {
      border: "border-red-500/30",
      glow: "from-red-500/35 via-orange-400/20 to-transparent",
      beam: "rgba(248,113,113,0.22)",
    },
    ufc_on_abc: {
      border: "border-blue-500/30",
      glow: "from-sky-500/35 via-cyan-400/20 to-transparent",
      beam: "rgba(96,165,250,0.22)",
    },
    tuf_finale: {
      border: "border-purple-500/30",
      glow: "from-purple-500/35 via-fuchsia-400/20 to-transparent",
      beam: "rgba(196,181,253,0.22)",
    },
    contender_series: {
      border: "border-emerald-500/30",
      glow: "from-emerald-500/35 via-teal-400/20 to-transparent",
      beam: "rgba(45,212,191,0.22)",
    },
    other: {
      border: "border-slate-500/30",
      glow: "from-slate-500/30 via-slate-400/20 to-transparent",
      beam: "rgba(148,163,184,0.18)",
    },
  };

  const accent = heroAccents[normalizedEventType] ?? heroAccents.other;
  const headliners = extractHeadliners(event.name);
  const isTitleBout = /title|championship|belt/i.test(event.name);

  // Group fights into sections
  const fightSections = groupFightsBySection(event.fight_card);

  return (
    <div className="container mx-auto px-4 py-8 text-white">
      <section
        className={`relative mb-10 overflow-hidden rounded-3xl border bg-slate-950/70 shadow-[0_25px_80px_rgba(15,23,42,0.55)] backdrop-blur-xl ${accent.border}`}
      >
        <div className="absolute inset-0">
          <div className="absolute inset-0 bg-[url('/textures/octagon-grid.svg')] opacity-40" style={{ animation: "hero-pan 36s linear infinite" }} />
          <div className={`absolute inset-0 bg-gradient-to-br ${accent.glow}`} />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.08),transparent_65%)]" />
          <div
            className="absolute -right-32 top-1/2 h-96 w-96 -translate-y-1/2 rounded-full"
            style={{ background: `radial-gradient(circle, ${accent.beam}, transparent 65%)` }}
          />
        </div>

        <div className="relative z-10 flex flex-col gap-10 px-6 py-12 sm:px-10 lg:flex-row">
          <div className="flex flex-1 flex-col gap-6">
            <Link
              href="/events"
              className="inline-flex w-fit items-center gap-3 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-sm text-white/70 transition hover:border-white/20 hover:bg-white/20"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to event index
            </Link>

            <div className="flex flex-wrap items-center gap-3">
              <span className={`inline-flex items-center rounded-full px-4 py-1 text-xs font-semibold uppercase tracking-[0.4em] text-white ${typeConfig.badgeClass}`}>
                {typeConfig.label}
              </span>
              <span
                className={`inline-flex items-center gap-2 rounded-full px-4 py-1 text-xs font-semibold uppercase tracking-[0.3em] ${
                  upcoming ? "bg-emerald-500/20 text-emerald-200" : "bg-slate-700/70 text-slate-200"
                }`}
              >
                <Clock className="h-3.5 w-3.5" />
                {upcoming ? "Upcoming" : "Completed"}
              </span>
              {isTitleBout && (
                <span className="inline-flex items-center gap-2 rounded-full border border-amber-400/50 bg-amber-400/15 px-4 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-amber-200">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Title Spotlight
                </span>
              )}
            </div>

            <div>
              <h1 className="text-4xl font-black leading-tight sm:text-5xl">{event.name}</h1>
              <p className="mt-3 text-sm uppercase tracking-[0.35em] text-white/60">{headliners}</p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <HeroMetadata icon={CalendarDays} label="Date" value={format(eventDate, "EEEE, MMMM d, yyyy")} />
              <HeroMetadata icon={MapPin} label="Location" value={event.location} />
              {event.venue && <HeroMetadata icon={Landmark} label="Venue" value={event.venue} />}
              {event.broadcast && <HeroMetadata icon={Tv} label="Broadcast" value={event.broadcast} />}
            </div>
          </div>

          <div className="w-full max-w-sm lg:w-auto">
            <div className="relative flex h-full flex-col gap-5 rounded-3xl border border-white/10 bg-white/5 p-6 shadow-inner">
              <div className="space-y-3">
                <p className="text-xs uppercase tracking-[0.3em] text-white/50">Countdown</p>
                <div className="flex items-end gap-3">
                  <span className="text-4xl font-black text-white">{countdownLabel}</span>
                  {upcoming && <Sparkles className="mb-1 h-5 w-5 text-amber-200" />}
                </div>
                <p className="text-xs text-white/60">{upcoming ? "Time until walkouts" : "Event has concluded"}</p>
              </div>

              <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

              <div className="space-y-4">
                <HeroMetadata icon={Globe2} label="Promotion" value={event.promotion} minimal />
                <HeroMetadata icon={CalendarDays} label="Local Time" value={format(eventDate, "hh:mm a zzz")} minimal />
                <HeroMetadata icon={MapPin} label="Arena" value={event.venue ?? "TBD"} minimal />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content - Fight Card */}
        <div className="lg:col-span-2 space-y-8">
          {/* Event Statistics Panel */}
          {event.fight_card.length > 0 && (
            <EventStatsPanel fights={event.fight_card} eventName={event.name} />
          )}

          {/* Fight Card Sections */}
          <div>
            <h2 className="text-2xl font-bold mb-6 text-white">
              Fight Card
            </h2>

            {event.fight_card.length === 0 ? (
              <div className="text-center py-12 bg-gray-800 rounded-lg text-gray-400 border border-gray-700">
                No fights available for this event.
              </div>
            ) : (
              <div className="space-y-6">
                {fightSections.map((section) => (
                  <FightCardSection
                    key={section.section}
                    section={section}
                    eventName={event.name}
                    allFights={event.fight_card}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Sidebar - Related Events */}
        <div className="lg:col-span-1">
          <div className="sticky top-8">
            {relatedEvents.length > 0 && (
              <RelatedEventsWidget
                currentEventId={event.event_id}
                relatedEvents={relatedEvents}
                reason="location"
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

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

interface HeroMetadataProps {
  icon: typeof CalendarDays;
  label: string;
  value: string;
  minimal?: boolean;
}

function HeroMetadata({ icon: Icon, label, value, minimal = false }: HeroMetadataProps) {
  return (
    <div
      className={clsx(
        "flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-3 py-3 text-white/80",
        minimal ? "bg-transparent border-white/5" : "shadow-inner",
      )}
    >
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
