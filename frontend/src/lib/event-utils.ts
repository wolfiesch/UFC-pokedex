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
   * Tailwind utility string describing the gradient/glassmorphism used for
   * event cards and hero backdrops.
   */
  cardGradient: string;
  /**
   * Narrow accent used for the EventCard spine and progress indicators.
   */
  spineGradient: string;
  /**
   * Soft glow applied to shadows and outlines for on-brand lighting cues.
   */
  glowShadow: string;
  /**
   * Overlay tint for hero sections so PPV/Fight Night experiences feel unique.
   */
  heroOverlay: string;
}

export const EVENT_TYPE_CONFIGS: Record<EventType, EventTypeConfig> = {
  ppv: {
    label: "PPV",
    color: "gold",
    bgClass: "bg-gradient-to-br from-amber-950 via-yellow-950 to-orange-950 border-amber-600",
    badgeClass: "bg-gradient-to-r from-amber-500 to-yellow-500 text-gray-900 font-bold",
    cardGradient:
      "bg-gradient-to-br from-amber-900/60 via-slate-950/70 to-orange-900/50 backdrop-blur",
    spineGradient: "bg-gradient-to-b from-amber-400 via-orange-400 to-red-500",
    glowShadow: "shadow-[0_0_35px_rgba(250,204,21,0.35)]",
    heroOverlay:
      "bg-gradient-to-br from-black/70 via-amber-900/60 to-transparent border-amber-500/60",
  },
  fight_night: {
    label: "Fight Night",
    color: "gray",
    bgClass: "bg-gray-800 border-gray-700",
    badgeClass: "bg-gray-600 text-white font-semibold",
    cardGradient:
      "bg-gradient-to-br from-slate-900/70 via-gray-900/70 to-slate-800/60 backdrop-blur",
    spineGradient: "bg-gradient-to-b from-slate-500 via-slate-400 to-slate-600",
    glowShadow: "shadow-[0_0_25px_rgba(148,163,184,0.3)]",
    heroOverlay:
      "bg-gradient-to-br from-black/75 via-slate-900/70 to-transparent border-slate-500/50",
  },
  ufc_on_espn: {
    label: "ESPN",
    color: "red",
    bgClass: "bg-gray-800 border-red-800",
    badgeClass: "bg-red-700 text-white font-semibold",
    cardGradient:
      "bg-gradient-to-br from-rose-950/70 via-gray-950/70 to-red-900/60 backdrop-blur",
    spineGradient: "bg-gradient-to-b from-red-500 via-red-400 to-orange-400",
    glowShadow: "shadow-[0_0_30px_rgba(248,113,113,0.3)]",
    heroOverlay:
      "bg-gradient-to-br from-black/75 via-rose-900/60 to-transparent border-red-500/60",
  },
  ufc_on_abc: {
    label: "ABC",
    color: "blue",
    bgClass: "bg-gray-800 border-blue-800",
    badgeClass: "bg-blue-700 text-white font-semibold",
    cardGradient:
      "bg-gradient-to-br from-blue-950/70 via-slate-950/70 to-sky-900/60 backdrop-blur",
    spineGradient: "bg-gradient-to-b from-sky-400 via-blue-400 to-indigo-500",
    glowShadow: "shadow-[0_0_30px_rgba(56,189,248,0.32)]",
    heroOverlay:
      "bg-gradient-to-br from-black/75 via-blue-900/60 to-transparent border-blue-500/60",
  },
  tuf_finale: {
    label: "TUF Finale",
    color: "purple",
    bgClass: "bg-gray-800 border-purple-800",
    badgeClass: "bg-purple-700 text-white font-semibold",
    cardGradient:
      "bg-gradient-to-br from-purple-950/70 via-violet-950/70 to-fuchsia-900/60 backdrop-blur",
    spineGradient: "bg-gradient-to-b from-fuchsia-400 via-purple-400 to-indigo-500",
    glowShadow: "shadow-[0_0_30px_rgba(192,132,252,0.32)]",
    heroOverlay:
      "bg-gradient-to-br from-black/75 via-purple-900/60 to-transparent border-purple-500/60",
  },
  contender_series: {
    label: "Contender Series",
    color: "green",
    bgClass: "bg-gray-800 border-green-800",
    badgeClass: "bg-green-700 text-white font-semibold",
    cardGradient:
      "bg-gradient-to-br from-emerald-950/70 via-slate-950/70 to-teal-900/60 backdrop-blur",
    spineGradient: "bg-gradient-to-b from-emerald-400 via-teal-400 to-emerald-500",
    glowShadow: "shadow-[0_0_30px_rgba(52,211,153,0.3)]",
    heroOverlay:
      "bg-gradient-to-br from-black/75 via-emerald-900/60 to-transparent border-emerald-500/60",
  },
  other: {
    label: "Other",
    color: "gray",
    bgClass: "bg-gray-800 border-gray-700",
    badgeClass: "bg-gray-600 text-white font-semibold",
    cardGradient:
      "bg-gradient-to-br from-neutral-900/70 via-stone-900/70 to-slate-900/60 backdrop-blur",
    spineGradient: "bg-gradient-to-b from-zinc-500 via-gray-500 to-neutral-500",
    glowShadow: "shadow-[0_0_25px_rgba(148,163,184,0.24)]",
    heroOverlay:
      "bg-gradient-to-br from-black/75 via-stone-900/60 to-transparent border-stone-500/60",
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
