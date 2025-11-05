/**
 * Utility functions for event classification and formatting
 */

export type EventType =
  | "ppv"
  | "fight_night"
  | "ufc_on_espn"
  | "ufc_on_abc"
  | "tuf_finale"
  | "contender_series"
  | "other";

export interface EventTypeConfig {
  label: string;
  color: string;
  bgClass: string;
  badgeClass: string;
}

export const EVENT_TYPE_CONFIGS: Record<EventType, EventTypeConfig> = {
  ppv: {
    label: "PPV",
    color: "gold",
    bgClass: "bg-gradient-to-br from-amber-950 via-yellow-950 to-orange-950 border-amber-600",
    badgeClass: "bg-gradient-to-r from-amber-500 to-yellow-500 text-gray-900 font-bold",
  },
  fight_night: {
    label: "Fight Night",
    color: "gray",
    bgClass: "bg-gray-800 border-gray-700",
    badgeClass: "bg-gray-600 text-white font-semibold",
  },
  ufc_on_espn: {
    label: "ESPN",
    color: "red",
    bgClass: "bg-gray-800 border-red-800",
    badgeClass: "bg-red-700 text-white font-semibold",
  },
  ufc_on_abc: {
    label: "ABC",
    color: "blue",
    bgClass: "bg-gray-800 border-blue-800",
    badgeClass: "bg-blue-700 text-white font-semibold",
  },
  tuf_finale: {
    label: "TUF Finale",
    color: "purple",
    bgClass: "bg-gray-800 border-purple-800",
    badgeClass: "bg-purple-700 text-white font-semibold",
  },
  contender_series: {
    label: "Contender Series",
    color: "green",
    bgClass: "bg-gray-800 border-green-800",
    badgeClass: "bg-green-700 text-white font-semibold",
  },
  other: {
    label: "Other",
    color: "gray",
    bgClass: "bg-gray-800 border-gray-700",
    badgeClass: "bg-gray-600 text-white font-semibold",
  },
};

export function detectEventType(eventName: string): EventType {
  const nameLower = eventName.toLowerCase();

  // PPV: UFC followed by a number (UFC 300, UFC 323)
  if (/^ufc\s+\d+:/.test(nameLower)) {
    return "ppv";
  }

  // Fight Night
  if (nameLower.includes("fight night")) {
    return "fight_night";
  }

  // UFC on ESPN
  if (nameLower.includes("ufc on espn") || nameLower.includes("espn")) {
    return "ufc_on_espn";
  }

  // UFC on ABC
  if (nameLower.includes("ufc on abc") || nameLower.includes("abc")) {
    return "ufc_on_abc";
  }

  // TUF Finale
  if (nameLower.includes("tuf") && nameLower.includes("finale")) {
    return "tuf_finale";
  }

  // Contender Series
  if (nameLower.includes("contender series") || nameLower.includes("dwcs")) {
    return "contender_series";
  }

  return "other";
}

export function getEventTypeLabel(eventType: EventType | null | undefined): string {
  if (!eventType) return "Other";
  return EVENT_TYPE_CONFIGS[eventType]?.label || "Other";
}

export function getEventTypeConfig(eventType: EventType | null | undefined): EventTypeConfig {
  if (!eventType) return EVENT_TYPE_CONFIGS.other;
  return EVENT_TYPE_CONFIGS[eventType] || EVENT_TYPE_CONFIGS.other;
}

export function normalizeEventType(value: string | null | undefined): EventType | null {
  if (!value) {
    return null;
  }

  if (value in EVENT_TYPE_CONFIGS) {
    return value as EventType;
  }

  return null;
}

export function isPPVEvent(eventName: string): boolean {
  return detectEventType(eventName) === "ppv";
}

export function groupEventsByMonth<T extends { date: string }>(
  events: T[]
): Map<string, T[]> {
  const grouped = new Map<string, T[]>();

  for (const event of events) {
    const date = new Date(event.date);
    const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;

    if (!grouped.has(monthKey)) {
      grouped.set(monthKey, []);
    }
    grouped.get(monthKey)!.push(event);
  }

  return grouped;
}

export function formatMonthYear(monthKey: string): string {
  const [year, month] = monthKey.split("-");
  const date = new Date(parseInt(year), parseInt(month) - 1);
  return date.toLocaleDateString("en-US", { month: "long", year: "numeric" });
}
