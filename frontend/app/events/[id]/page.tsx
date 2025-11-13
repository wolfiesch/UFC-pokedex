"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { format, formatDistanceStrict, parseISO } from "date-fns";
import { groupFightsBySection, isTitleFight } from "@/lib/fight-utils";
import { detectEventType, getEventTypeConfig, normalizeEventType } from "@/lib/event-utils";
import EventStatsPanel from "@/components/events/EventStatsPanel";
import FightCardSection from "@/components/events/FightCardSection";
import RelatedEventsWidget from "@/components/events/RelatedEventsWidget";
import { CalendarDays, Globe2, MapPin, Timer, Tv } from "lucide-react";

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

  // Group fights into sections
  const fightSections = groupFightsBySection(event.fight_card);

  const heroCountdown = formatDistanceStrict(parseISO(event.date), new Date(), { addSuffix: true });
  const titleFightCount = event.fight_card.filter((fight) => isTitleFight(fight, event.name)).length;

  return (
    <div className="mx-auto max-w-7xl px-4 pb-16">
      <div className="relative mt-8 overflow-hidden rounded-[3rem] border border-white/10 bg-slate-950/80 shadow-[0_60px_160px_rgba(15,23,42,0.6)] backdrop-blur-xl">
        <div className={`absolute inset-0 ${typeConfig.heroOverlay}`} aria-hidden />
        <div className="absolute inset-0" style={{
          backgroundImage:
            "radial-gradient(circle at 20% 20%, rgba(59,130,246,0.25), transparent 55%), radial-gradient(circle at 80% 30%, rgba(236,72,153,0.25), transparent 60%), linear-gradient(140deg, rgba(2,6,23,0.9) 0%, rgba(15,23,42,0.75) 100%)",
        }} aria-hidden />

        <div className="relative grid gap-10 p-8 sm:p-12 lg:grid-cols-[2fr,1fr]">
          <div className="space-y-6">
            <Link
              href="/events"
              className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-slate-200 transition-colors hover:border-white/40"
            >
              <span className="text-lg">←</span> Back to events
            </Link>

            <div className="flex flex-wrap items-center gap-3">
              <span className={`inline-flex items-center gap-2 rounded-full border border-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] ${typeConfig.badgeClass}`}>
                {typeConfig.label}
              </span>
              <span
                className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] ${
                  event.status === "upcoming"
                    ? "border-emerald-400/60 bg-emerald-500/10 text-emerald-100"
                    : "border-white/20 bg-white/10 text-slate-200"
                }`}
              >
                {event.status === "upcoming" ? "Upcoming" : "Completed"}
              </span>
              {isPPV && (
                <span className="inline-flex items-center gap-2 rounded-full border border-amber-400/70 bg-amber-500/20 px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-amber-100">
                  PPV Spotlight
                </span>
              )}
            </div>

            <div className="space-y-4 text-white">
              <h1 className="text-4xl font-semibold leading-tight sm:text-5xl lg:text-6xl">
                {event.name}
              </h1>
              <p className="text-sm uppercase tracking-[0.35em] text-slate-300">
                {format(parseISO(event.date), "EEEE, MMMM d yyyy")} · {heroCountdown}
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-white/15 bg-white/5 p-4 text-sm text-slate-200">
                <div className="flex items-center gap-2">
                  <CalendarDays className="h-4 w-4 text-slate-300" aria-hidden />
                  {format(parseISO(event.date), "p zzzz")}
                </div>
                {event.broadcast && (
                  <div className="mt-2 flex items-center gap-2">
                    <Tv className="h-4 w-4 text-slate-300" aria-hidden />
                    {event.broadcast}
                  </div>
                )}
              </div>
              <div className="rounded-2xl border border-white/15 bg-white/5 p-4 text-sm text-slate-200">
                {event.location && (
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-slate-300" aria-hidden />
                    {event.location}
                  </div>
                )}
                {event.venue && (
                  <div className="mt-2 flex items-center gap-2">
                    <Globe2 className="h-4 w-4 text-slate-300" aria-hidden />
                    {event.venue}
                  </div>
                )}
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
                <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Countdown</p>
                <p className="mt-2 flex items-center gap-2 text-lg font-semibold text-white">
                  <Timer className="h-5 w-5 text-emerald-300" aria-hidden />
                  {heroCountdown}
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
                <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Story beat</p>
                <p className="mt-2 text-white">
                  Dive into the full fight card below to explore tale-of-the-tape narratives, finish trends, and card momentum.
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-col justify-between gap-6">
            <div className="rounded-3xl border border-white/10 bg-white/5 p-6 text-sm text-slate-200">
              <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Broadcast info</p>
              <div className="mt-4 space-y-2">
                <p>Official start: {format(parseISO(event.date), "p")}</p>
                <p className="text-slate-300">Status: {event.status}</p>
              </div>
            </div>
            <div className="rounded-3xl border border-white/10 bg-white/5 p-6 text-sm text-slate-200">
              <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Event dossier</p>
              <ul className="mt-3 space-y-2">
                <li>Fight card size: {event.fight_card.length} bouts</li>
                <li>Title fights: {titleFightCount}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

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
