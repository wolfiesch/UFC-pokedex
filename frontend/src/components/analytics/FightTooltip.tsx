/**
 * Tooltip component for fight scatter visualization
 * Displays detailed fight information on hover
 */

import type { ScatterFight } from "@/types/fight-scatter";
import { format } from "date-fns";

interface FightTooltipProps {
  fight: ScatterFight;
  x: number;
  y: number;
}

const RESULT_COLORS = {
  W: "#2ecc71",
  L: "#e74c3c",
  D: "#95a5a6",
};

const METHOD_LABELS = {
  KO: "KO/TKO",
  SUB: "Submission",
  DEC: "Decision",
  OTHER: "Other",
};

/**
 * Formats finish time as "Round X, MM:SS" or "Decision"
 */
function formatFinishTime(
  method: string,
  round: number | null | undefined,
  time: string | null | undefined
): string {
  if (method === "DEC") {
    return "Decision";
  }

  if (round && time) {
    return `Round ${round}, ${time}`;
  }

  return "Unknown";
}

export function FightTooltip({ fight, x, y }: FightTooltipProps) {
  // Position tooltip to avoid going off-screen
  const tooltipX = x > window.innerWidth / 2 ? x - 220 : x + 20;
  const tooltipY = y > window.innerHeight / 2 ? y - 120 : y + 20;

  return (
    <div
      className="pointer-events-none fixed z-50"
      style={{
        left: `${tooltipX}px`,
        top: `${tooltipY}px`,
      }}
    >
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-3 shadow-xl">
        {/* Result Badge */}
        <div className="mb-2 flex items-center justify-between gap-3">
          <span
            className="inline-block rounded px-2 py-0.5 text-xs font-bold text-white"
            style={{ backgroundColor: RESULT_COLORS[fight.result] }}
          >
            {fight.result === "W" ? "WIN" : fight.result === "L" ? "LOSS" : "DRAW"}
          </span>
          <span className="text-xs text-gray-400">
            {METHOD_LABELS[fight.method]}
          </span>
        </div>

        {/* Opponent */}
        <div className="mb-2">
          <div className="text-sm font-semibold text-white">
            vs {fight.opponent_name}
          </div>
        </div>

        {/* Event */}
        <div className="mb-1 text-xs text-gray-300">{fight.event_name}</div>

        {/* Date */}
        <div className="mb-2 text-xs text-gray-400">
          {format(new Date(fight.date), "MMM d, yyyy")}
        </div>

        {/* Finish Time */}
        <div className="text-xs text-gray-300">
          {formatFinishTime(fight.method, fight.round, fight.time)}
        </div>

        {/* Link to UFCStats */}
        {fight.fight_card_url && (
          <div className="mt-2 border-t border-gray-700 pt-2">
            <a
              href={fight.fight_card_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-400 hover:text-blue-300 hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              View on UFCStats →
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
