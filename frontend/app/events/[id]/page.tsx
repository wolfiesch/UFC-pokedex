"use client";

import { Suspense, useMemo } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams } from "next/navigation";
import { format, parseISO } from "date-fns";

import { useEventDetails } from "@/hooks/useEventDetails";
import { groupFightsBySection } from "@/lib/fight-utils";
import { detectEventType, getEventTypeConfig } from "@/lib/event-utils";

const EventStatsPanel = dynamic(() => import("@/components/events/EventStatsPanel"), {
  ssr: false,
  suspense: true,
});

const FightCardSection = dynamic(() => import("@/components/events/FightCardSection"), {
  ssr: false,
  suspense: true,
});

const RelatedEventsWidget = dynamic(
  () => import("@/components/events/RelatedEventsWidget"),
  {
    ssr: false,
    suspense: true,
  }
);

const statsFallback = (
  <div className="rounded-lg border border-gray-700 bg-gray-800/30 p-6 text-gray-400">
    Loading event metrics…
  </div>
);

const cardFallback = (
  <div className="space-y-4">
    <div className="h-12 rounded-lg bg-gray-800/40 animate-pulse" />
    <div className="h-32 rounded-lg bg-gray-800/40 animate-pulse" />
    <div className="h-32 rounded-lg bg-gray-800/40 animate-pulse" />
  </div>
);

const relatedFallback = (
  <div className="rounded-lg border border-gray-700 bg-gray-800/40 p-5 text-gray-400">
    Loading nearby events…
  </div>
);

export default function EventDetailPage() {
  const params = useParams();
  const eventId = (params?.id as string | undefined) ?? "";

  const { event, relatedEvents, isLoading, error } = useEventDetails(eventId, {
    relatedLimit: 6,
  });

  const eventType = useMemo(() => {
    if (!event) {
      return "other";
    }
    return event.event_type || detectEventType(event.name);
  }, [event]);

  const typeConfig = useMemo(() => getEventTypeConfig(eventType), [eventType]);
  const isPPV = eventType === "ppv";

  const fightSections = useMemo(() => {
    if (!event) {
      return [];
    }
    return groupFightsBySection(event.fight_card);
  }, [event]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading event…</div>
      </div>
    );
  }

  if (error || !event) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="mb-4 text-2xl font-bold text-red-500">Error</h1>
          <p className="text-gray-400">{error?.message ?? "Event not found"}</p>
          <Link href="/events" className="mt-4 inline-block text-blue-500 hover:underline">
            ← Back to Events
          </Link>
        </div>
      </div>
    );
  }

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
            <Suspense fallback={statsFallback}>
              <EventStatsPanel fights={event.fight_card} eventName={event.name} />
            </Suspense>
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
                <Suspense fallback={cardFallback}>
                  {fightSections.map((section) => (
                    <FightCardSection
                      key={section.section}
                      section={section}
                      eventName={event.name}
                      allFights={event.fight_card}
                    />
                  ))}
                </Suspense>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar - Related Events */}
        <div className="lg:col-span-1">
          <div className="sticky top-8">
            {relatedEvents.length > 0 && (
              <Suspense fallback={relatedFallback}>
                <RelatedEventsWidget
                  currentEventId={event.event_id}
                  relatedEvents={relatedEvents}
                  reason="location"
                />
              </Suspense>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
