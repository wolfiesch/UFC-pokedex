"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { format, parseISO } from "date-fns";
import { groupFightsBySection } from "@/lib/fight-utils";
import { detectEventType, getEventTypeConfig } from "@/lib/event-utils";
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
  const eventType = event.event_type || detectEventType(event.name);
  const typeConfig = getEventTypeConfig(eventType);
  const isPPV = eventType === "ppv";

  // Group fights into sections
  const fightSections = groupFightsBySection(event.fight_card);

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Back Button */}
      <Link href="/events" className="inline-flex items-center gap-2 text-blue-500 hover:underline mb-6">
        ← Back to Events
      </Link>

      {/* Event Header */}
      <div
        className={`
          rounded-lg p-6 mb-8 border
          ${isPPV ? "bg-gradient-to-br from-amber-950 via-yellow-950 to-orange-950 border-amber-600" : "bg-gray-800 border-gray-700"}
        `}
      >
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="flex-1">
            <div className="mb-2 flex items-center gap-2 flex-wrap">
              <span className={`rounded px-3 py-1 text-xs font-bold ${typeConfig.badgeClass}`}>
                {typeConfig.label}
              </span>
              <span
                className={`px-3 py-1 rounded-full text-xs font-medium ${
                  event.status === "upcoming"
                    ? "bg-green-900 text-green-300"
                    : "bg-gray-700 text-gray-300"
                }`}
              >
                {event.status === "upcoming" ? "Upcoming" : "Completed"}
              </span>
            </div>
            <h1 className={`text-3xl font-bold ${isPPV ? "text-amber-200" : "text-white"}`}>
              {event.name}
            </h1>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="flex items-center gap-2 text-gray-400">
            <span className="text-gray-500">📅</span>
            <span>{format(parseISO(event.date), "MMMM d, yyyy")}</span>
          </div>
          {event.location && (
            <div className="flex items-center gap-2 text-gray-400">
              <span className="text-gray-500">📍</span>
              <span>{event.location}</span>
            </div>
          )}
          {event.venue && (
            <div className="flex items-center gap-2 text-gray-400">
              <span className="text-gray-500">🏟️</span>
              <span>{event.venue}</span>
            </div>
          )}
          {event.broadcast && (
            <div className="flex items-center gap-2 text-gray-400">
              <span className="text-gray-500">📺</span>
              <span>{event.broadcast}</span>
            </div>
          )}
        </div>

        {isPPV && (
          <div className="mt-4 pt-4 border-t border-amber-600/40">
            <span className="font-bold text-amber-300">⭐ Pay-Per-View Event</span>
          </div>
        )}
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
