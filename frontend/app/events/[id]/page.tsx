"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { format, parseISO } from "date-fns";
import {
  ArrowLeft,
  CalendarDays,
  Clock,
  Flame,
  MapPin,
  Tv,
  Building2,
  Trophy,
  Globe2,
} from "lucide-react";
import { groupFightsBySection } from "@/lib/fight-utils";
import { detectEventType, getEventTypeConfig, normalizeEventType } from "@/lib/event-utils";
import EventStatsPanel from "@/components/events/EventStatsPanel";
import FightCardSection from "@/components/events/FightCardSection";
import RelatedEventsWidget from "@/components/events/RelatedEventsWidget";

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

const EVENT_TYPE_BACKDROPS: Record<string, string> = {
  ppv: "https://images.unsplash.com/photo-1521412644187-c49fa049e84d?auto=format&fit=crop&w=1600&q=80",
  fight_night: "https://images.unsplash.com/photo-1489515217757-5fd1be406fef?auto=format&fit=crop&w=1600&q=80",
  ufc_on_espn: "https://images.unsplash.com/photo-1517842645767-c639042777db?auto=format&fit=crop&w=1600&q=80",
  ufc_on_abc: "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?auto=format&fit=crop&w=1600&q=80",
  tuf_finale: "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?auto=format&fit=crop&w=1600&q=80",
  contender_series: "https://images.unsplash.com/photo-1521737604893-d14cc237f11d?auto=format&fit=crop&w=1600&q=80",
  other: "https://images.unsplash.com/photo-1509223197845-458d87318791?auto=format&fit=crop&w=1600&q=80",
};

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

        const response = await fetch(`${apiUrl}/events/${eventId}`, {
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch event: ${response.statusText}`);
        }

        const data = await response.json();
        setEvent(data);

        if (data.location) {
          try {
            const relatedResponse = await fetch(
              `${apiUrl}/events/search/?location=${encodeURIComponent(data.location)}&limit=6`,
              { cache: "no-store" },
            );
            if (relatedResponse.ok) {
              const relatedData = await relatedResponse.json();
              setRelatedEvents(relatedData.events || []);
            }
          } catch (err) {
            console.error("Error fetching related events:", err);
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
      <div className="min-h-screen bg-slate-950 text-white">
        <div className="mx-auto flex min-h-screen max-w-6xl flex-col items-center justify-center gap-6 px-4">
          <div className="h-12 w-12 animate-spin rounded-full border-2 border-white/30 border-t-emerald-400" />
          <p className="text-lg font-semibold tracking-[0.3em] text-white/70">Loading event dossier…</p>
        </div>
      </div>
    );
  }

  if (error || !event) {
    return (
      <div className="min-h-screen bg-slate-950 text-white">
        <div className="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center gap-6 px-4 text-center">
          <p className="text-3xl font-black text-rose-300">Event unavailable</p>
          <p className="text-sm text-white/70">{error || "The requested fight card could not be located."}</p>
          <Link
            href="/events"
            className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-5 py-2 text-sm font-semibold text-white transition hover:border-white/40 hover:bg-white/20"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Return to events
          </Link>
        </div>
      </div>
    );
  }

  const normalizedEventType =
    normalizeEventType(event.event_type) ?? detectEventType(event.name);
  const typeConfig = getEventTypeConfig(normalizedEventType);
  const isPPV = normalizedEventType === "ppv";

  const [title, tagline] = event.name.includes(":")
    ? event.name.split(":").map((segment) => segment.trim())
    : [event.name, "Full headline reveal coming soon"];

  const viewerTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  const posterImage = EVENT_TYPE_BACKDROPS[normalizedEventType ?? "other"] ?? EVENT_TYPE_BACKDROPS.other;

  const countdownLabel = (() => {
    const now = new Date();
    const eventDate = parseISO(event.date);

    if (event.status !== "upcoming") {
      return "Completed";
    }

    if (eventDate <= now) {
      return "Live now";
    }

    const diffMs = eventDate.getTime() - now.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor((diffMs / (1000 * 60 * 60)) % 24);

    if (diffDays <= 0) {
      return `${diffHours}h to go`;
    }

    return `${diffDays}d ${diffHours}h remaining`;
  })();

  const fightSections = groupFightsBySection(event.fight_card);

  const highlightIsTitleFight = (() => {
    const text = `${event.name} ${event.fight_card.map((fight) => fight.weight_class ?? "").join(" ")}`.toLowerCase();
    return text.includes("title") || text.includes("championship");
  })();

  return (
    <div className="relative min-h-screen bg-slate-950 text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(148,163,184,0.16),transparent_55%)]" />
      <div className="relative z-10 mx-auto max-w-6xl px-4 pb-16">
        <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-900/60 shadow-[0_30px_80px_-40px_rgba(14,116,144,0.6)]">
          <div
            className="absolute inset-0"
            aria-hidden="true"
            style={{
              backgroundImage:
                `linear-gradient(130deg, rgba(15,23,42,0.95) 0%, rgba(15,23,42,0.55) 55%, rgba(15,23,42,0.85) 100%), url('${posterImage}')`,
              backgroundSize: "cover",
              backgroundPosition: "center",
            }}
          />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(244,114,182,0.2),transparent_60%)] mix-blend-soft-light opacity-50" aria-hidden="true" />
          <div className="relative flex flex-col gap-10 px-8 py-12 sm:px-12 lg:flex-row">
            <div className="flex-1 space-y-6">
              <Link
                href="/events"
                className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-white/70 transition hover:border-white/30 hover:bg-white/20"
              >
                <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to schedule
              </Link>
              <div className="flex flex-wrap items-center gap-3 text-xs font-semibold uppercase tracking-[0.3em] text-white/70">
                <span className={`rounded-full px-3 py-1 text-[0.65rem] font-black uppercase tracking-[0.4em] ${typeConfig.badgeClass}`}>
                  {typeConfig.label}
                </span>
                <span
                  className={`inline-flex items-center gap-2 rounded-full px-4 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.3em] ${
                    event.status === "upcoming"
                      ? "bg-emerald-500/20 text-emerald-100"
                      : "bg-blue-500/20 text-blue-100"
                  }`}
                >
                  <Clock className="h-3 w-3" aria-hidden="true" />
                  {countdownLabel}
                </span>
                {highlightIsTitleFight && (
                  <span className="inline-flex items-center gap-2 rounded-full border border-amber-300/50 bg-amber-400/20 px-4 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.3em] text-amber-100">
                    <Trophy className="h-3 w-3" aria-hidden="true" /> Title implications
                  </span>
                )}
              </div>
              <div>
                <h1 className={`text-4xl font-black drop-shadow-md sm:text-5xl ${isPPV ? "text-amber-100" : "text-white"}`}>
                  {title}
                </h1>
                <p className="mt-4 max-w-2xl text-base text-white/80">{tagline}</p>
              </div>
              <div className="grid gap-4 text-sm text-white/80 sm:grid-cols-2">
                <div className="flex items-center gap-2">
                  <CalendarDays className="h-4 w-4 text-white/60" aria-hidden="true" />
                  <span>{format(parseISO(event.date), "MMMM d, yyyy")}</span>
                </div>
                {event.location && (
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-white/60" aria-hidden="true" />
                    <span>{event.location}</span>
                  </div>
                )}
                {event.venue && (
                  <div className="flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-white/60" aria-hidden="true" />
                    <span>{event.venue}</span>
                  </div>
                )}
                {event.broadcast && (
                  <div className="flex items-center gap-2">
                    <Tv className="h-4 w-4 text-white/60" aria-hidden="true" />
                    <span>{event.broadcast}</span>
                  </div>
                )}
              </div>
            </div>

            <aside className="w-full max-w-sm space-y-5">
              <div className="rounded-3xl border border-white/10 bg-white/10 p-6 backdrop-blur">
                <p className="text-xs font-semibold uppercase tracking-[0.3em] text-white/60">Event telemetry</p>
                <div className="mt-4 space-y-4 text-sm text-white/80">
                  <div className="flex items-start gap-3">
                    <Flame className="mt-1 h-4 w-4 text-amber-300" aria-hidden="true" />
                    <div>
                      <p className="text-xs uppercase tracking-[0.3em] text-white/60">Promotion</p>
                      <p className="text-sm font-semibold text-white">{event.promotion}</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <Globe2 className="mt-1 h-4 w-4 text-sky-300" aria-hidden="true" />
                    <div>
                      <p className="text-xs uppercase tracking-[0.3em] text-white/60">Viewer timezone</p>
                      <p className="text-sm font-semibold text-white">{viewerTimeZone}</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <Clock className="mt-1 h-4 w-4 text-emerald-300" aria-hidden="true" />
                    <div>
                      <p className="text-xs uppercase tracking-[0.3em] text-white/60">Countdown</p>
                      <p className="text-sm font-semibold text-white">{countdownLabel}</p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="rounded-3xl border border-white/10 bg-white/5 p-6 text-xs text-white/70 backdrop-blur">
                <p className="font-semibold uppercase tracking-[0.3em]">What to watch</p>
                <p className="mt-3 leading-relaxed">
                  Explore the complete fight card below for match order, bout details, and historical context. Bookmark the UFC
                  Stats link for live round-by-round scoring during fight night.
                </p>
              </div>
            </aside>
          </div>
        </section>

        <div className="mt-12 grid grid-cols-1 gap-10 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-8">
            {event.fight_card.length > 0 && (
              <EventStatsPanel fights={event.fight_card} eventName={event.name} />
            )}

            <div>
              <h2 className="text-2xl font-bold text-white">Fight Card</h2>
              {event.fight_card.length === 0 ? (
                <div className="mt-6 text-center text-white/70">No fights available for this event.</div>
              ) : (
                <div className="mt-6 space-y-6">
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

          <div className="lg:col-span-1">
            <div className="sticky top-8 space-y-6">
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
    </div>
  );
}
