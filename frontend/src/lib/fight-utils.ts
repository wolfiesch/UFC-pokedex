/**
 * Utility functions for fight card processing and analysis
 */

export interface Fight {
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

export type CardSection = "main" | "prelims" | "early_prelims";

export interface FightCardSection {
  section: CardSection;
  label: string;
  fights: Fight[];
}

/**
 * Detect if a fight is a title fight based on event name, fighter names, or keywords
 */
export function isTitleFight(fight: Fight, eventName: string): boolean {
  const searchText = `${eventName} ${fight.fighter_1_name} ${fight.fighter_2_name}`.toLowerCase();

  const titleKeywords = [
    "championship",
    "title",
    "belt",
    "champion vs",
    "vs champion",
    "interim",
  ];

  return titleKeywords.some(keyword => searchText.includes(keyword));
}

/**
 * Detect if a fight is the main event (typically the first fight in the card)
 */
export function isMainEvent(fight: Fight, fights: Fight[], eventName: string): boolean {
  // Main event is usually the first fight
  const isFirstFight = fights.indexOf(fight) === 0;

  // Also check if it's mentioned in the event name
  const fightMentionedInName = eventName.toLowerCase().includes(fight.fighter_1_name.toLowerCase()) ||
                                eventName.toLowerCase().includes(fight.fighter_2_name.toLowerCase());

  return isFirstFight || fightMentionedInName;
}

/**
 * Group fights into sections (Main Card, Prelims, Early Prelims)
 * Based on typical UFC card structure:
 * - First 5-6 fights: Main Card
 * - Next 4 fights: Prelims
 * - Remaining: Early Prelims
 */
export function groupFightsBySection(fights: Fight[]): FightCardSection[] {
  const totalFights = fights.length;

  if (totalFights === 0) {
    return [];
  }

  const sections: FightCardSection[] = [];

  // Typical card structure
  const mainCardSize = Math.min(6, Math.ceil(totalFights / 2));
  const prelimsSize = Math.min(4, totalFights - mainCardSize);

  // Main Card - first fights
  if (mainCardSize > 0) {
    sections.push({
      section: "main",
      label: "Main Card",
      fights: fights.slice(0, mainCardSize),
    });
  }

  // Prelims - middle fights
  if (prelimsSize > 0) {
    sections.push({
      section: "prelims",
      label: "Prelims",
      fights: fights.slice(mainCardSize, mainCardSize + prelimsSize),
    });
  }

  // Early Prelims - remaining fights
  const earlyPrelimsSize = totalFights - mainCardSize - prelimsSize;
  if (earlyPrelimsSize > 0) {
    sections.push({
      section: "early_prelims",
      label: "Early Prelims",
      fights: fights.slice(mainCardSize + prelimsSize),
    });
  }

  return sections;
}

/**
 * Get fight outcome color based on result
 */
export function getFightOutcomeColor(result: string | null): string {
  if (!result || result === "N/A") return "bg-gray-700 text-gray-300";

  const resultLower = result.toLowerCase();

  if (resultLower.includes("win") || resultLower === "w") {
    return "bg-green-700 text-green-100";
  }

  if (resultLower.includes("loss") || resultLower === "l") {
    return "bg-red-700 text-red-100";
  }

  if (resultLower.includes("draw") || resultLower === "d") {
    return "bg-yellow-700 text-yellow-100";
  }

  if (resultLower.includes("nc") || resultLower.includes("no contest")) {
    return "bg-gray-600 text-gray-200";
  }

  return "bg-gray-700 text-gray-300";
}

/**
 * Parse fighter record string into wins, losses, draws
 */
export function parseRecord(record: string | null): { wins: number; losses: number; draws: number } | null {
  if (!record) return null;

  // Format: "17-8-0" or "17-8" (W-L-D)
  const parts = record.split("-").map(n => parseInt(n, 10));

  if (parts.length < 2 || parts.some(isNaN)) {
    return null;
  }

  return {
    wins: parts[0] || 0,
    losses: parts[1] || 0,
    draws: parts[2] || 0,
  };
}

/**
 * Calculate statistics for an event
 */
export interface EventStats {
  totalFights: number;
  mainCardFights: number;
  prelimFights: number;
  titleFights: number;
  weightClasses: string[];
  finishes: number;
  decisions: number;
  weightClassBreakdown: { name: string; fights: number; percentage: number }[];
  fastestFinish: {
    label: string;
    round: number | null;
    time: string | null;
  } | null;
  dominantFinishMethod: string | null;
}

export function calculateEventStats(fights: Fight[], eventName: string): EventStats {
  const sections = groupFightsBySection(fights);

  const weightClasses = Array.from(
    new Set(
      fights
        .map(f => f.weight_class)
        .filter((wc): wc is string => wc !== null && wc !== "")
    )
  );

  const finishes = fights.filter(f =>
    f.method &&
    !f.method.toLowerCase().includes("decision") &&
    !f.method.toLowerCase().includes("n/a")
  ).length;

  const decisions = fights.filter(f =>
    f.method &&
    f.method.toLowerCase().includes("decision")
  ).length;

  const titleFights = fights.filter(f => isTitleFight(f, eventName)).length;

  const mainCardSection = sections.find(s => s.section === "main");
  const prelimSection = sections.find(s => s.section === "prelims");

  const weightClassCounts = fights.reduce<Record<string, number>>((acc, fight) => {
    if (fight.weight_class) {
      acc[fight.weight_class] = (acc[fight.weight_class] || 0) + 1;
    }
    return acc;
  }, {});

  const weightClassBreakdown = Object.entries(weightClassCounts)
    .sort(([, countA], [, countB]) => countB - countA)
    .map(([name, fightsCount]) => ({
      name,
      fights: fightsCount,
      percentage: fights.length > 0 ? Math.round((fightsCount / fights.length) * 100) : 0,
    }));

  const timeToSeconds = (round: number | null, time: string | null): number => {
    if (!round || !time) return Number.POSITIVE_INFINITY;
    const [minutes, seconds] = time.split(":").map(part => parseInt(part, 10));
    if (Number.isNaN(minutes) || Number.isNaN(seconds)) {
      return Number.POSITIVE_INFINITY;
    }
    return (round - 1) * 300 + minutes * 60 + seconds; // 5 minute rounds
  };

  const finishFights = fights.filter(f =>
    f.method &&
    !f.method.toLowerCase().includes("decision") &&
    !f.method.toLowerCase().includes("n/a")
  );

  const fastestFinish = finishFights.reduce<{
    fight: Fight | null;
    seconds: number;
  }>(
    (acc, fight) => {
      const seconds = timeToSeconds(fight.round, fight.time);
      if (seconds < acc.seconds) {
        return { fight, seconds };
      }
      return acc;
    },
    { fight: null, seconds: Number.POSITIVE_INFINITY }
  ).fight;

  const dominantFinishMethod = finishFights.reduce<Record<string, number>>((acc, fight) => {
    const key = fight.method?.trim() ?? "";
    if (!key) return acc;
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const mostCommonFinish = Object.entries(dominantFinishMethod)
    .sort(([, countA], [, countB]) => countB - countA)[0]?.[0] ?? null;

  return {
    totalFights: fights.length,
    mainCardFights: mainCardSection?.fights.length || 0,
    prelimFights: prelimSection?.fights.length || 0,
    titleFights,
    weightClasses,
    finishes,
    decisions,
    weightClassBreakdown,
    fastestFinish: fastestFinish
      ? {
          label: `${fastestFinish.fighter_1_name} vs ${fastestFinish.fighter_2_name}`,
          round: fastestFinish.round,
          time: fastestFinish.time,
        }
      : null,
    dominantFinishMethod: mostCommonFinish,
  };
}
