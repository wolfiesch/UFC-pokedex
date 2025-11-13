"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { differenceInDays, differenceInHours, format, parseISO } from "date-fns";
import { groupFightsBySection } from "@/lib/fight-utils";
import { detectEventType, getEventTypeConfig, normalizeEventType } from "@/lib/event-utils";
import EventStatsPanel from "@/components/events/EventStatsPanel";
import FightCardSection from "@/components/events/FightCardSection";
import RelatedEventsWidget from "@/components/events/RelatedEventsWidget";
import {
  ArrowLeft,
  BadgeCheck,
  CalendarDays,
  Clock,
  Flame,
  MapPin,
  Radio,
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

  // Group fights into sections
  const fightSections = groupFightsBySection(event.fight_card);
  const eventDate = parseISO(event.date);
  const countdown = getCountdown(event.status, eventDate);
  const [promotionPrefix, headlineSegment] = event.name.split(":");
  const headlinerNames = headlineSegment?.split("vs").map((fighter) => fighter.trim()).filter(Boolean) ?? [];

  return (
    <div className="mx-auto max-w-6xl px-4 pb-16 pt-10">
      <div className="relative mb-12 overflow-hidden rounded-[42px] border border-white/10 bg-slate-950 shadow-[0_60px_140px_-80px_rgba(15,23,42,0.95)]">
        <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1546519638-68e109498ffc?auto=format&fit=crop&w=1600&q=80')] bg-cover bg-center opacity-50" />
        <div className={`absolute inset-0 bg-gradient-to-br ${typeConfig.heroGlow} via-transparent to-slate-950`} />
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/60 to-transparent" />

        <div className="relative z-10 flex flex-col gap-10 px-6 pb-12 pt-10 md:px-12 md:pb-16">
          <div className="flex items-center justify-between text-xs uppercase tracking-[0.4em] text-slate-200/70">
            <Link
              href="/events"
              className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 font-semibold text-slate-100 transition hover:border-white/40 hover:bg-white/20"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to events
            </Link>
            <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 font-semibold text-slate-200">
              {promotionPrefix?.trim() ?? "UFC"}
            </span>
          </div>

          <div className="grid gap-8 md:grid-cols-[1.35fr_0.65fr] md:items-end">
            <div className="space-y-6 text-slate-100">
              <div className="flex flex-wrap items-center gap-3">
                <span className={`inline-flex items-center gap-2 rounded-full px-4 py-1 text-xs font-semibold uppercase tracking-[0.35em] text-slate-900 shadow ${typeConfig.badgeClass}`}>
                  <Sparkles className="h-4 w-4" aria-hidden="true" />
                  {typeConfig.label}
                </span>
                <span
                  className={`inline-flex items-center gap-2 rounded-full px-4 py-1 text-xs font-semibold uppercase tracking-[0.35em] ${
                    event.status === "upcoming" ? "bg-emerald-400/20 text-emerald-100" : "bg-slate-700/60 text-slate-200"
                  }`}
                >
                  <BadgeCheck className="h-4 w-4" aria-hidden="true" />
                  {event.status === "upcoming" ? "Scheduled" : "Completed"}
                </span>
                {isPPV && (
                  <span className="inline-flex items-center gap-2 rounded-full border border-amber-300/60 bg-amber-400/20 px-4 py-1 text-xs font-semibold uppercase tracking-[0.35em] text-amber-100">
                    <Flame className="h-4 w-4" aria-hidden="true" /> Championship billing
                  </span>
                )}
              </div>

              <div>
                <h1 className="text-4xl font-black uppercase tracking-tight drop-shadow md:text-5xl">
                  {headlineSegment?.trim() ?? event.name}
                </h1>
                {headlinerNames.length >= 2 && (
                  <p className="mt-3 text-sm font-medium uppercase tracking-[0.6em] text-slate-200/80">
                    {headlinerNames.join(" • ")}
                  </p>
                )}
              </div>

              <div className="grid gap-4 text-sm sm:grid-cols-2">
                <div className="flex items-center gap-3 rounded-3xl border border-white/15 bg-white/10 px-4 py-3">
                  <CalendarDays className="h-4 w-4 text-cyan-300" aria-hidden="true" />
                  <div>
                    <p className="text-[0.65rem] uppercase tracking-[0.4em] text-slate-300/70">Date</p>
                    <p className="text-base font-semibold text-white">{format(eventDate, "MMMM d, yyyy")}</p>
                  </div>
                </div>
                {event.location && (
                  <div className="flex items-center gap-3 rounded-3xl border border-white/15 bg-white/10 px-4 py-3">
                    <MapPin className="h-4 w-4 text-rose-300" aria-hidden="true" />
                    <div>
                      <p className="text-[0.65rem] uppercase tracking-[0.4em] text-slate-300/70">Location</p>
                      <p className="text-base font-semibold text-white">{event.location}</p>
                    </div>
                  </div>
                )}
                {event.venue && (
                  <div className="flex items-center gap-3 rounded-3xl border border-white/15 bg-white/10 px-4 py-3">
                    <Radio className="h-4 w-4 text-amber-300" aria-hidden="true" />
                    <div>
                      <p className="text-[0.65rem] uppercase tracking-[0.4em] text-slate-300/70">Venue</p>
                      <p className="text-base font-semibold text-white">{event.venue}</p>
                    </div>
                  </div>
                )}
                {event.broadcast && (
                  <div className="flex items-center gap-3 rounded-3xl border border-white/15 bg-white/10 px-4 py-3">
                    <Tv className="h-4 w-4 text-indigo-300" aria-hidden="true" />
                    <div>
                      <p className="text-[0.65rem] uppercase tracking-[0.4em] text-slate-300/70">Broadcast</p>
                      <p className="text-base font-semibold text-white">{event.broadcast}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <aside className="flex flex-col gap-4 rounded-[32px] border border-white/15 bg-white/10 p-5 text-slate-100 backdrop-blur">
              <p className="text-xs font-semibold uppercase tracking-[0.45em] text-slate-300/80">Event timeline</p>
              <div className="flex flex-col gap-3 text-sm">
                <div className="flex items-start gap-3">
                  <Clock className="h-4 w-4 text-cyan-300" aria-hidden="true" />
                  <div>
                    <p className="text-[0.65rem] uppercase tracking-[0.4em] text-slate-300/80">Countdown</p>
                    <p className="text-base font-semibold text-white">{countdown}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Flame className="h-4 w-4 text-amber-300" aria-hidden="true" />
                  <div>
                    <p className="text-[0.65rem] uppercase tracking-[0.4em] text-slate-300/80">Promotion</p>
                    <p className="text-base font-semibold text-white">{event.promotion}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Sparkles className="h-4 w-4 text-emerald-300" aria-hidden="true" />
                  <div>
                    <p className="text-[0.65rem] uppercase tracking-[0.4em] text-slate-300/80">Status</p>
                    <p className="text-base font-semibold text-white">{event.status}</p>
                  </div>
                </div>
              </div>
            </aside>
          </div>
        </div>
      </div>

      <div className="grid gap-10 lg:grid-cols-[1.55fr_0.45fr]">
        <div className="space-y-8">
          {event.fight_card.length > 0 && (
            <EventStatsPanel fights={event.fight_card} eventName={event.name} />
          )}

          <div>
            <h2 className="mb-6 text-2xl font-bold uppercase tracking-[0.3em] text-slate-100">Fight Card</h2>

            {event.fight_card.length === 0 ? (
              <div className="rounded-3xl border border-white/10 bg-white/5 py-12 text-center text-slate-300">
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

function getCountdown(status: string, eventDate: Date): string {
  if (status !== "upcoming") {
    return "Relive the action";
  }

  const now = new Date();
  if (eventDate <= now) {
    return "Fight night";
  }

  const days = differenceInDays(eventDate, now);
  if (days > 0) {
    return `${days} day${days === 1 ? "" : "s"}`;
  }

  const hours = differenceInHours(eventDate, now);
  return `${hours} hour${hours === 1 ? "" : "s"}`;
}
