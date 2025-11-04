import type { FightHistoryEntry } from "./types";

/**
 * Parsed fight record structure
 */
export interface ParsedRecord {
  wins: number;
  losses: number;
  draws: number;
  total: number;
  winPercentage: number;
}

/**
 * Streak information
 */
export interface Streak {
  type: "win" | "loss" | "draw" | "none";
  count: number;
  label: string;
}

/**
 * Last fight summary
 */
export interface LastFightInfo {
  opponent: string;
  result: string;
  method: string;
  date: string | null;
  eventName: string;
}

/**
 * Parse a fight record string like "20-5-1" into structured data
 */
export function parseRecord(record?: string | null): ParsedRecord | null {
  if (!record) return null;

  const parts = record.split("-").map((p) => parseInt(p.trim(), 10));

  if (parts.length < 2 || parts.some(isNaN)) {
    return null;
  }

  const wins = parts[0] ?? 0;
  const losses = parts[1] ?? 0;
  const draws = parts[2] ?? 0;
  const total = wins + losses + draws;

  const winPercentage = total > 0 ? Math.round((wins / total) * 100) : 0;

  return {
    wins,
    losses,
    draws,
    total,
    winPercentage,
  };
}

/**
 * Calculate the current win/loss/draw streak from fight history
 * Fight history should be sorted by date (most recent first)
 */
export function calculateStreak(fightHistory?: FightHistoryEntry[]): Streak {
  if (!fightHistory || fightHistory.length === 0) {
    return { type: "none", count: 0, label: "No fights" };
  }

  // Sort by date descending (most recent first)
  const sortedFights = [...fightHistory].sort((a, b) => {
    const dateA = a.event_date ? new Date(a.event_date).getTime() : 0;
    const dateB = b.event_date ? new Date(b.event_date).getTime() : 0;
    return dateB - dateA;
  });

  const firstFight = sortedFights[0];
  if (!firstFight) {
    return { type: "none", count: 0, label: "No fights" };
  }

  // Normalize result to lowercase for comparison
  const firstResult = firstFight.result.toLowerCase().trim();
  let streakType: "win" | "loss" | "draw" | "none" = "none";

  // Handle various result formats: "win", "w", "loss", "l", "draw", "d"
  if (firstResult === "w" || firstResult.includes("win")) {
    streakType = "win";
  } else if (firstResult === "l" || firstResult.includes("loss")) {
    streakType = "loss";
  } else if (firstResult === "d" || firstResult.includes("draw")) {
    streakType = "draw";
  }

  if (streakType === "none") {
    return { type: "none", count: 0, label: "No streak" };
  }

  // Count consecutive results of the same type
  let count = 0;
  for (const fight of sortedFights) {
    const result = fight.result.toLowerCase().trim();

    // Handle various result formats: "win"/"w", "loss"/"l", "draw"/"d"
    const isWin = result === "w" || result.includes("win");
    const isLoss = result === "l" || result.includes("loss");
    const isDraw = result === "d" || result.includes("draw");

    if (
      (streakType === "win" && isWin) ||
      (streakType === "loss" && isLoss) ||
      (streakType === "draw" && isDraw)
    ) {
      count++;
    } else {
      break; // Streak broken
    }
  }

  // Only show streaks of 2 or more
  if (count < 2) {
    return { type: "none", count: 0, label: "No streak" };
  }

  // Label is just the number (e.g., "15" instead of "15 wins")
  const label = `${count}`;

  return { type: streakType, count, label };
}

/**
 * Get the most recent fight from fight history
 */
export function getLastFight(fightHistory?: FightHistoryEntry[]): LastFightInfo | null {
  if (!fightHistory || fightHistory.length === 0) {
    return null;
  }

  // Sort by date descending (most recent first)
  const sortedFights = [...fightHistory].sort((a, b) => {
    const dateA = a.event_date ? new Date(a.event_date).getTime() : 0;
    const dateB = b.event_date ? new Date(b.event_date).getTime() : 0;
    return dateB - dateA;
  });

  const lastFight = sortedFights[0];
  if (!lastFight) {
    return null;
  }

  return {
    opponent: lastFight.opponent,
    result: lastFight.result,
    method: lastFight.method,
    date: lastFight.event_date || null,
    eventName: lastFight.event_name,
  };
}

/**
 * Format a fight date for display
 * @param date - ISO date string or null
 * @returns Formatted date string like "Jan 15, 2024" or "Unknown date"
 */
export function formatFightDate(date: string | null): string {
  if (!date) return "Unknown date";

  try {
    const parsedDate = new Date(date);
    if (isNaN(parsedDate.getTime())) {
      return "Unknown date";
    }

    return parsedDate.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return "Unknown date";
  }
}

/**
 * Get a relative time string like "2 months ago"
 */
export function getRelativeTime(date: string | null): string {
  if (!date) return "";

  try {
    const parsedDate = new Date(date);
    if (isNaN(parsedDate.getTime())) {
      return "";
    }

    const now = new Date();
    const diffMs = now.getTime() - parsedDate.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays < 1) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
    return `${Math.floor(diffDays / 365)} years ago`;
  } catch {
    return "";
  }
}
