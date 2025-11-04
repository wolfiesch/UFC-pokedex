"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { format, parseISO } from "date-fns";

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
}

export default function EventDetailPage() {
  const params = useParams();
  const eventId = params?.id as string;
  const [event, setEvent] = useState<EventDetail | null>(null);
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

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Back Button */}
      <Link href="/events" className="inline-flex items-center gap-2 text-blue-500 hover:underline mb-6">
        ← Back to Events
      </Link>

      {/* Event Header */}
      <div className="bg-gray-800 rounded-lg p-6 mb-8 border border-gray-700">
        <div className="flex items-start justify-between mb-4">
          <h1 className="text-3xl font-bold text-white">{event.name}</h1>
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
      </div>

      {/* Fight Card */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-4">
          Fight Card ({event.fight_card.length} {event.fight_card.length === 1 ? "Fight" : "Fights"})
        </h2>
      </div>

      <div className="space-y-4">
        {event.fight_card.length === 0 ? (
          <div className="text-center py-12 bg-gray-800 rounded-lg text-gray-400">
            No fights available for this event.
          </div>
        ) : (
          event.fight_card.map((fight, index) => (
            <div
              key={fight.fight_id}
              className="bg-gray-800 rounded-lg p-6 border border-gray-700"
            >
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-medium text-gray-500">
                  Fight {index + 1}
                  {fight.weight_class && ` • ${fight.weight_class}`}
                </span>
                {fight.result && fight.result !== "N/A" && (
                  <span className="text-xs px-2 py-1 bg-gray-700 text-gray-300 rounded">
                    {fight.result.toUpperCase()}
                  </span>
                )}
              </div>

              {/* Fighters */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center mb-4">
                <Link
                  href={`/fighters/${fight.fighter_1_id}`}
                  className="text-center md:text-right hover:text-blue-400 transition-colors"
                >
                  <div className="text-lg font-bold">{fight.fighter_1_name}</div>
                </Link>

                <div className="text-center text-gray-500 font-bold">VS</div>

                <Link
                  href={fight.fighter_2_id ? `/fighters/${fight.fighter_2_id}` : "#"}
                  className={`text-center md:text-left ${
                    fight.fighter_2_id ? "hover:text-blue-400 transition-colors" : ""
                  }`}
                >
                  <div className="text-lg font-bold">{fight.fighter_2_name}</div>
                </Link>
              </div>

              {/* Fight Details */}
              {(fight.method || fight.round || fight.time) && (
                <div className="flex flex-wrap gap-4 text-sm text-gray-400 pt-4 border-t border-gray-700">
                  {fight.method && (
                    <div>
                      <span className="text-gray-500">Method:</span>{" "}
                      <span className="text-white">{fight.method}</span>
                    </div>
                  )}
                  {fight.round && (
                    <div>
                      <span className="text-gray-500">Round:</span>{" "}
                      <span className="text-white">{fight.round}</span>
                    </div>
                  )}
                  {fight.time && (
                    <div>
                      <span className="text-gray-500">Time:</span>{" "}
                      <span className="text-white">{fight.time}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
