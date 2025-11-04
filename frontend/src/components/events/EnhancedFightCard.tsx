"use client";

import { Fight, getFightOutcomeColor, parseRecord } from "@/lib/fight-utils";

interface EnhancedFightCardProps {
  fight: Fight;
  isTitleFight?: boolean;
  isMainEvent?: boolean;
  fighterRecord?: string | null; // fighter_1's record from detail page
}

/**
 * Enhanced fight card component with fighter records and visual styling
 */
export default function EnhancedFightCard({
  fight,
  isTitleFight = false,
  isMainEvent = false,
  fighterRecord,
}: EnhancedFightCardProps) {
  const outcomeColor = getFightOutcomeColor(fight.result);
  const parsedRecord = fighterRecord ? parseRecord(fighterRecord) : null;

  return (
    <div
      className={`
        relative rounded-lg border p-4 transition-all hover:shadow-lg
        ${isMainEvent ? "border-amber-500 bg-gradient-to-br from-amber-950/40 to-orange-950/40" : "border-gray-700 bg-gray-800/50"}
      `}
    >
      {/* Title Fight Badge */}
      {isTitleFight && (
        <div className="absolute -top-2 -right-2 z-10">
          <span className="inline-flex items-center gap-1 rounded-full bg-gradient-to-r from-yellow-500 to-amber-500 px-3 py-1 text-xs font-bold text-gray-900 shadow-lg">
            👑 Title Fight
          </span>
        </div>
      )}

      {/* Main Event Badge */}
      {isMainEvent && !isTitleFight && (
        <div className="absolute -top-2 -right-2 z-10">
          <span className="inline-flex items-center gap-1 rounded-full bg-gradient-to-r from-red-600 to-rose-600 px-3 py-1 text-xs font-bold text-white shadow-lg">
            ⭐ Main Event
          </span>
        </div>
      )}

      <div className="space-y-3">
        {/* Fighter 1 */}
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <span className="text-lg font-bold text-white">
                {fight.fighter_1_name}
              </span>
              {parsedRecord && (
                <span className="rounded-md bg-gray-700 px-2 py-1 text-xs font-medium text-gray-300">
                  {parsedRecord.wins}-{parsedRecord.losses}-{parsedRecord.draws}
                </span>
              )}
            </div>
          </div>
          {fight.result && (
            <span
              className={`ml-3 rounded-md px-3 py-1 text-sm font-bold ${outcomeColor}`}
            >
              {fight.result}
            </span>
          )}
        </div>

        {/* VS Divider */}
        <div className="flex items-center gap-2">
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-gray-600 to-transparent" />
          <span className="text-xs font-bold text-gray-500">VS</span>
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-gray-600 to-transparent" />
        </div>

        {/* Fighter 2 */}
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <span className="text-lg font-medium text-gray-300">
              {fight.fighter_2_name}
            </span>
          </div>
        </div>

        {/* Fight Details */}
        {(fight.weight_class || fight.method) && (
          <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-gray-700 pt-3 text-sm text-gray-400">
            {fight.weight_class && (
              <span className="flex items-center gap-1">
                <span className="font-medium text-gray-500">Weight Class:</span>
                {fight.weight_class}
              </span>
            )}
            {fight.method && (
              <span className="flex items-center gap-1">
                <span className="font-medium text-gray-500">Method:</span>
                {fight.method}
              </span>
            )}
            {fight.round && fight.time && (
              <span className="flex items-center gap-1">
                <span className="font-medium text-gray-500">Time:</span>
                R{fight.round} {fight.time}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
