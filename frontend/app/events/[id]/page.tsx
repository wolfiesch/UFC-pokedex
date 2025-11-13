"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { format, formatDistanceToNowStrict, parseISO } from "date-fns";
import { groupFightsBySection, isTitleFight } from "@/lib/fight-utils";
import { detectEventType, getEventTypeConfig, normalizeEventType } from "@/lib/event-utils";
import EventStatsPanel from "@/components/events/EventStatsPanel";
import FightCardSection from "@/components/events/FightCardSection";
import RelatedEventsWidget from "@/components/events/RelatedEventsWidget";
import type { EventType } from "@/lib/event-utils";
import {
  ArrowLeft,
  BadgeCheck,
  CalendarDays,
  Clock3,
  MapPin,
  Radio,
  Sparkles,
  Tv2,
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

const EVENT_TYPE_ARTWORK: Record<EventType, string> = {
  ppv: "https://images.unsplash.com/photo-1571008887538-b36bb32f4571?auto=format&fit=crop&w=1600&q=80",
  fight_night: "https://images.unsplash.com/photo-1521410132144-1a1e55e26f58?auto=format&fit=crop&w=1600&q=80",
  ufc_on_espn: "https://images.unsplash.com/photo-1546519638-68e109498ffc?auto=format&fit=crop&w=1600&q=80",
  ufc_on_abc: "https://images.unsplash.com/photo-1471295253337-3ceaaedca402?auto=format&fit=crop&w=1600&q=80",
  tuf_finale: "https://images.unsplash.com/photo-1525954677600-06e3f1c41c08?auto=format&fit=crop&w=1600&q=80",
  contender_series: "https://images.unsplash.com/photo-1533560904424-4b9d0f06e5d4?auto=format&fit=crop&w=1600&q=80",
  other: "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=1600&q=80",
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

  const heroBackground = EVENT_TYPE_ARTWORK[(normalizedEventType ?? "other") as EventType];
  const headliner = event.name.split(":")[1]?.trim();
  const countdownLabel =
    event.status === "upcoming"
      ? `${formatDistanceToNowStrict(parseISO(event.date), { addSuffix: false })}`
      : "Event complete";
  const metadata = [
    {
      label: "Date",
      value: format(parseISO(event.date), "EEEE, MMMM d"),
      icon: CalendarDays,
    },
    {
      label: "Location",
      value: event.location,
      icon: MapPin,
    },
    {
      label: "Venue",
      value: event.venue,
      icon: Radio,
    },
    {
      label: "Broadcast",
      value: event.broadcast,
      icon: Tv2,
    },
    {
      label: "Local time",
      value: format(parseISO(event.date), "p zzz"),
      icon: Clock3,
    },
  ].filter((item) => Boolean(item.value));
  const hasTitleFight = event.fight_card.some((fight) => isTitleFight(fight, event.name));

  return (
    <div className="relative mx-auto flex max-w-6xl flex-col gap-10 px-4 pb-24">
      <div className="relative overflow-hidden rounded-[40px] border border-white/10 bg-slate-950/90 px-8 py-14 shadow-[0_60px_140px_-100px_rgba(15,23,42,0.95)]">
        <div
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            backgroundImage: `linear-gradient(135deg, rgba(8,11,19,0.9), rgba(8,11,19,0.6)), url(${heroBackground})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.25),_transparent_55%)]" />

        <div className="relative z-10 flex flex-col gap-10 lg:flex-row lg:items-end lg:justify-between">
          <div className="flex-1 space-y-6">
            <Link
              href="/events"
              className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.35em] text-slate-300 transition hover:text-white"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden /> Back to events
            </Link>

            <div className="flex flex-wrap items-center gap-3">
              <span className={`rounded-full px-4 py-1 text-xs font-semibold uppercase tracking-[0.3em] ${typeConfig.badgeClass}`}>
                {typeConfig.label}
              </span>
              <span
                className={`inline-flex items-center gap-2 rounded-full border px-4 py-1 text-xs font-semibold uppercase tracking-[0.25em] ${
                  event.status === "upcoming"
                    ? "border-emerald-400/60 bg-emerald-500/10 text-emerald-200"
                    : "border-slate-300/40 bg-slate-200/10 text-slate-200"
                }`}
              >
                <BadgeCheck className="h-4 w-4" aria-hidden />
                {event.status === "upcoming" ? "Upcoming" : "Completed"}
              </span>
              {isPPV && (
                <span className="inline-flex items-center gap-2 rounded-full border border-amber-400/50 bg-amber-500/10 px-4 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-amber-200">
                  PPV Spotlight
                </span>
              )}
            </div>

            <h1 className="text-balance text-4xl font-black tracking-tight text-white sm:text-5xl">
              {event.name}
            </h1>
            {headliner && <p className="text-lg font-semibold text-slate-200/80">{headliner}</p>}

            <div className="flex flex-wrap items-center gap-4">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-slate-200">
                <Clock3 className="h-4 w-4" aria-hidden />
                {countdownLabel}
              </div>
              {hasTitleFight && (
                <div className="inline-flex items-center gap-3 rounded-full border border-amber-400/60 bg-amber-500/15 px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-amber-100">
                  <Sparkles className="h-4 w-4" aria-hidden /> Title on the line
                </div>
              )}
            </div>
          </div>

          <div className="flex w-full max-w-xs flex-col gap-4 rounded-3xl border border-white/10 bg-white/10 p-6 backdrop-blur">
            {metadata.map((item) => (
              <div key={item.label} className="flex items-start gap-3">
                <div className="mt-1 h-8 w-8 flex-shrink-0 rounded-full border border-white/20 bg-white/10 text-sky-200">
                  <item.icon className="h-full w-full p-1.5" aria-hidden />
                </div>
                <div>
                  <p className="text-[0.65rem] uppercase tracking-[0.3em] text-slate-400">{item.label}</p>
                  <p className="text-sm font-semibold text-white">{item.value}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
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
