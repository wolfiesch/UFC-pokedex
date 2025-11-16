"use client";

import Link from "next/link";
import { Fight, getFightOutcomeColor } from "@/lib/fight-utils";
import { useFighterInfo } from "@/hooks/useFighterInfo";

interface EnhancedFightCardProps {
  fight: Fight;
  isTitleFight?: boolean;
  isMainEvent?: boolean;
}

/**
 * Enhanced fight card component displaying fighters side-by-side in matchup format
 */
export default function EnhancedFightCard({
  fight,
  isTitleFight = false,
  isMainEvent = false,
}: EnhancedFightCardProps) {
  // Fetch fighter information
  const { fighterInfo: fighter1Info } = useFighterInfo(fight.fighter_1_id);
  const { fighterInfo: fighter2Info } = useFighterInfo(fight.fighter_2_id);

  // Determine winner/loser for visual styling
  const fighter1Won = fight.result?.toLowerCase().includes("win");
  const fighter2Won = fight.result?.toLowerCase().includes("loss");
  const isDraw = fight.result?.toLowerCase().includes("draw");
  const isNoContest = fight.result?.toLowerCase().includes("nc") || fight.result?.toLowerCase().includes("no contest");

  return (
    <div
      className={`
        relative rounded-lg border p-5 transition-all hover:shadow-lg
        ${isMainEvent ? "border-amber-500 bg-gradient-to-br from-amber-950/40 to-orange-950/40" : "border-gray-700 bg-gray-800/50"}
      `}
    >
      {/* Title Fight Badge */}
      {isTitleFight && (
        <div className="absolute -right-2 -top-2 z-10">
          <span className="inline-flex items-center gap-1 rounded-full bg-gradient-to-r from-yellow-500 to-amber-500 px-3 py-1 text-xs font-bold text-gray-900 shadow-lg">
            👑 Title Fight
          </span>
        </div>
      )}

      {/* Main Event Badge */}
      {isMainEvent && !isTitleFight && (
        <div className="absolute -right-2 -top-2 z-10">
          <span className="inline-flex items-center gap-1 rounded-full bg-gradient-to-r from-red-600 to-rose-600 px-3 py-1 text-xs font-bold text-white shadow-lg">
            ⭐ Main Event
          </span>
        </div>
      )}

      {/* Matchup Layout */}
      <div className="flex items-center gap-4">
        {/* Fighter 1 - Left Side */}
        <div className={`flex-1 text-left ${fighter1Won ? "opacity-100" : fighter2Won ? "opacity-60" : "opacity-100"}`}>
          <Link
            href={`/fighters/${fight.fighter_1_id}`}
            className="group inline-block"
          >
            <div className="text-lg font-bold text-white transition-colors group-hover:text-blue-400">
              {fight.fighter_1_name}
            </div>
          </Link>

          {/* Fighter 1 Info (Record & Ranking) */}
          <div className="mt-1 flex flex-wrap items-center gap-2">
            {fighter1Info?.record && (
              <span className="text-xs text-gray-400">
                {fighter1Info.record}
              </span>
            )}
            {fighter1Info?.is_current_champion && (
              <span className="inline-block rounded bg-yellow-600 px-1.5 py-0.5 text-xs font-bold text-gray-900">
                👑 CHAMP
              </span>
            )}
            {!fighter1Info?.is_current_champion && fighter1Info?.current_rank && (
              <span className="inline-block rounded bg-blue-600 px-1.5 py-0.5 text-xs font-bold text-white">
                #{fighter1Info.current_rank}
              </span>
            )}
          </div>

          {fighter1Won && (
            <div className="mt-1">
              <span className="inline-block rounded-md bg-green-600 px-2 py-0.5 text-xs font-bold text-white">
                ✓ WINNER
              </span>
            </div>
          )}
        </div>

        {/* VS Divider with Result */}
        <div className="flex flex-col items-center gap-2">
          <div className="flex items-center gap-2">
            <div className="h-px w-8 bg-gradient-to-r from-transparent via-gray-500 to-gray-500" />
            <span className="text-sm font-bold text-gray-400">VS</span>
            <div className="h-px w-8 bg-gradient-to-l from-transparent via-gray-500 to-gray-500" />
          </div>
          {(isDraw || isNoContest) && (
            <span className={`rounded-md px-2 py-0.5 text-xs font-bold ${
              isDraw ? "bg-yellow-600 text-gray-900" : "bg-gray-600 text-white"
            }`}>
              {isDraw ? "DRAW" : "NC"}
            </span>
          )}
        </div>

        {/* Fighter 2 - Right Side */}
        <div className={`flex-1 text-right ${fighter2Won ? "opacity-100" : fighter1Won ? "opacity-60" : "opacity-100"}`}>
          <Link
            href={`/fighters/${fight.fighter_2_id || "#"}`}
            className="group inline-block"
          >
            <div className="text-lg font-bold text-white transition-colors group-hover:text-blue-400">
              {fight.fighter_2_name}
            </div>
          </Link>

          {/* Fighter 2 Info (Record & Ranking) */}
          <div className="mt-1 flex flex-wrap items-center justify-end gap-2">
            {fighter2Info?.is_current_champion && (
              <span className="inline-block rounded bg-yellow-600 px-1.5 py-0.5 text-xs font-bold text-gray-900">
                👑 CHAMP
              </span>
            )}
            {!fighter2Info?.is_current_champion && fighter2Info?.current_rank && (
              <span className="inline-block rounded bg-blue-600 px-1.5 py-0.5 text-xs font-bold text-white">
                #{fighter2Info.current_rank}
              </span>
            )}
            {fighter2Info?.record && (
              <span className="text-xs text-gray-400">
                {fighter2Info.record}
              </span>
            )}
          </div>

          {fighter2Won && (
            <div className="mt-1">
              <span className="inline-block rounded-md bg-green-600 px-2 py-0.5 text-xs font-bold text-white">
                ✓ WINNER
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Fight Details */}
      {(fight.weight_class || fight.method || fight.round) && (
        <div className="mt-4 flex flex-wrap items-center justify-center gap-3 border-t border-gray-700 pt-3 text-sm text-gray-400">
          {fight.weight_class && (
            <span className="inline-block rounded-full bg-purple-600/20 px-3 py-1 text-xs font-medium text-purple-300 border border-purple-600/30">
              {fight.weight_class}
            </span>
          )}
          {fight.method && (
            <span className="flex items-center gap-1">
              <span className="font-medium text-gray-500">Method:</span>
              <span className="text-gray-300">{fight.method}</span>
            </span>
          )}
          {fight.round && fight.time && (
            <span className="flex items-center gap-1">
              <span className="font-medium text-gray-500">Time:</span>
              <span className="text-gray-300">R{fight.round} {fight.time}</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
}
