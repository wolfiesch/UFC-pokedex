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
  /**
   * Accent gradient leveraged for hero lighting and high-emphasis components.
   */
  heroGlow: string;
  /**
   * Subtle translucent background used for glassmorphic surfaces.
   */
  cardSurface: string;
  /**
   * Vertical spine / border color for asymmetric cards.
   */
  spineClass: string;
  /**
   * Optional background image token that can be swapped for themed assets.
   */
  backdropTexture: string;
}

export const EVENT_TYPE_CONFIGS: Record<EventType, EventTypeConfig> = {
  ppv: {
    label: "PPV",
    color: "gold",
    bgClass: "bg-gradient-to-br from-amber-950 via-yellow-950 to-orange-950 border-amber-600",
    badgeClass: "bg-gradient-to-r from-amber-500 to-yellow-500 text-gray-900 font-bold",
    heroGlow: "from-amber-400/80 via-orange-500/30 to-rose-500/40",
    cardSurface: "bg-white/5",
    spineClass: "bg-gradient-to-b from-amber-500 via-orange-500 to-red-500",
    backdropTexture: "bg-[radial-gradient(circle_at_top,_rgba(255,204,128,0.35)_0%,_rgba(17,17,17,0.15)_55%,_rgba(0,0,0,0.9)_100%)]",
  },
  fight_night: {
    label: "Fight Night",
    color: "gray",
    bgClass: "bg-gray-800 border-gray-700",
    badgeClass: "bg-gray-600 text-white font-semibold",
    heroGlow: "from-slate-400/40 via-slate-500/20 to-slate-800/60",
    cardSurface: "bg-white/3",
    spineClass: "bg-gradient-to-b from-slate-400 via-slate-500 to-slate-700",
    backdropTexture: "bg-[radial-gradient(circle_at_top,_rgba(148,163,184,0.25)_0%,_rgba(30,41,59,0.4)_50%,_rgba(15,23,42,0.8)_100%)]",
  },
  ufc_on_espn: {
    label: "ESPN",
    color: "red",
    bgClass: "bg-gray-800 border-red-800",
    badgeClass: "bg-red-700 text-white font-semibold",
    heroGlow: "from-red-500/50 via-orange-500/20 to-slate-900/70",
    cardSurface: "bg-white/4",
    spineClass: "bg-gradient-to-b from-red-500 via-rose-500 to-red-700",
    backdropTexture: "bg-[radial-gradient(circle_at_top,_rgba(248,113,113,0.35)_0%,_rgba(30,41,59,0.3)_45%,_rgba(15,23,42,0.85)_100%)]",
  },
  ufc_on_abc: {
    label: "ABC",
    color: "blue",
    bgClass: "bg-gray-800 border-blue-800",
    badgeClass: "bg-blue-700 text-white font-semibold",
    heroGlow: "from-sky-400/60 via-blue-500/30 to-slate-900/80",
    cardSurface: "bg-white/4",
    spineClass: "bg-gradient-to-b from-sky-400 via-blue-500 to-indigo-600",
    backdropTexture: "bg-[radial-gradient(circle_at_top,_rgba(125,211,252,0.35)_0%,_rgba(30,64,175,0.35)_55%,_rgba(15,23,42,0.85)_100%)]",
  },
  tuf_finale: {
    label: "TUF Finale",
    color: "purple",
    bgClass: "bg-gray-800 border-purple-800",
    badgeClass: "bg-purple-700 text-white font-semibold",
    heroGlow: "from-purple-400/60 via-fuchsia-500/25 to-slate-900/70",
    cardSurface: "bg-white/4",
    spineClass: "bg-gradient-to-b from-purple-500 via-fuchsia-500 to-purple-700",
    backdropTexture: "bg-[radial-gradient(circle_at_top,_rgba(216,180,254,0.35)_0%,_rgba(91,33,182,0.3)_50%,_rgba(15,23,42,0.85)_100%)]",
  },
  contender_series: {
    label: "Contender Series",
    color: "green",
    bgClass: "bg-gray-800 border-green-800",
    badgeClass: "bg-green-700 text-white font-semibold",
    heroGlow: "from-emerald-400/60 via-green-500/25 to-slate-900/70",
    cardSurface: "bg-white/4",
    spineClass: "bg-gradient-to-b from-emerald-400 via-green-500 to-emerald-700",
    backdropTexture: "bg-[radial-gradient(circle_at_top,_rgba(167,243,208,0.35)_0%,_rgba(22,101,52,0.3)_55%,_rgba(15,23,42,0.85)_100%)]",
  },
  other: {
    label: "Other",
    color: "gray",
    bgClass: "bg-gray-800 border-gray-700",
    badgeClass: "bg-gray-600 text-white font-semibold",
    heroGlow: "from-zinc-300/40 via-zinc-500/20 to-slate-900/70",
    cardSurface: "bg-white/4",
    spineClass: "bg-gradient-to-b from-zinc-400 via-zinc-500 to-zinc-700",
    backdropTexture: "bg-[radial-gradient(circle_at_top,_rgba(212,212,216,0.25)_0%,_rgba(39,39,42,0.35)_55%,_rgba(9,9,11,0.85)_100%)]",
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
