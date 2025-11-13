"use client";

/**
 * Demo component showing FightScatter usage
 * Can be integrated into fighter detail pages or analytics dashboards
 */

import { useState } from "react";
import { FightScatter } from "./FightScatter";
import { convertFightToScatterPoint } from "@/lib/fight-scatter-utils";
import type { FightHistoryEntry } from "@/lib/types";
import type { FightResult, FightMethod } from "@/types/fight-scatter";

interface FightScatterDemoProps {
  fightHistory: FightHistoryEntry[];
}

export function FightScatterDemo({ fightHistory }: FightScatterDemoProps) {
  const [showDensity, setShowDensity] = useState(false);
  const [showTrend, setShowTrend] = useState(true);
  const [filterResults, setFilterResults] = useState<FightResult[]>([]);
  const [filterMethods, setFilterMethods] = useState<FightMethod[]>([]);

  // Convert fight history to scatter points
  const scatterFights = fightHistory.map((fight) =>
    convertFightToScatterPoint(fight),
  );

  const handleSelectFight = (fightId: string) => {
    console.log("Selected fight:", fightId);
    // Navigate to fight detail or show modal
  };

  const toggleResultFilter = (result: FightResult) => {
    setFilterResults((prev) =>
      prev.includes(result)
        ? prev.filter((r) => r !== result)
        : [...prev, result],
    );
  };

  const toggleMethodFilter = (method: FightMethod) => {
    setFilterMethods((prev) =>
      prev.includes(method)
        ? prev.filter((m) => m !== method)
        : [...prev, method],
    );
  };

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Overlay Toggles */}
        <div className="flex gap-2">
          <button
            onClick={() => setShowDensity(!showDensity)}
            className={`rounded px-3 py-1.5 text-sm font-medium transition-colors ${
              showDensity
                ? "bg-blue-600 text-white hover:bg-blue-700"
                : "bg-gray-200 text-gray-700 hover:bg-gray-300"
            }`}
          >
            {showDensity ? "Hide" : "Show"} Density
          </button>
          <button
            onClick={() => setShowTrend(!showTrend)}
            className={`rounded px-3 py-1.5 text-sm font-medium transition-colors ${
              showTrend
                ? "bg-blue-600 text-white hover:bg-blue-700"
                : "bg-gray-200 text-gray-700 hover:bg-gray-300"
            }`}
          >
            {showTrend ? "Hide" : "Show"} Trend
          </button>
        </div>

        <div className="h-6 w-px bg-gray-300" />

        {/* Result Filters */}
        <div className="flex gap-2">
          <span className="text-sm font-medium text-gray-600">Results:</span>
          {(["W", "L", "D"] as FightResult[]).map((result) => (
            <button
              key={result}
              onClick={() => toggleResultFilter(result)}
              className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                filterResults.length === 0 || filterResults.includes(result)
                  ? result === "W"
                    ? "bg-green-600 text-white"
                    : result === "L"
                      ? "bg-red-600 text-white"
                      : "bg-gray-600 text-white"
                  : "bg-gray-200 text-gray-400"
              }`}
            >
              {result === "W" ? "Wins" : result === "L" ? "Losses" : "Draws"}
            </button>
          ))}
        </div>

        <div className="h-6 w-px bg-gray-300" />

        {/* Method Filters */}
        <div className="flex gap-2">
          <span className="text-sm font-medium text-gray-600">Methods:</span>
          {(["KO", "SUB", "DEC"] as FightMethod[]).map((method) => (
            <button
              key={method}
              onClick={() => toggleMethodFilter(method)}
              className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                filterMethods.length === 0 || filterMethods.includes(method)
                  ? "bg-blue-600 text-white hover:bg-blue-700"
                  : "bg-gray-200 text-gray-400 hover:bg-gray-300"
              }`}
            >
              {method}
            </button>
          ))}
        </div>

        {/* Clear Filters */}
        {(filterResults.length > 0 || filterMethods.length > 0) && (
          <button
            onClick={() => {
              setFilterResults([]);
              setFilterMethods([]);
            }}
            className="text-sm text-blue-600 hover:text-blue-700 hover:underline"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Chart */}
      <div className="rounded-lg border border-gray-300 bg-white p-4">
        <div className="mb-2 text-sm font-medium text-gray-700">
          Fight History Timeline
        </div>
        <FightScatter
          fights={scatterFights}
          showDensity={showDensity}
          showTrend={showTrend}
          filterResults={filterResults}
          filterMethods={filterMethods}
          onSelectFight={handleSelectFight}
          height={600}
        />
      </div>

      {/* Legend */}
      <div className="flex items-center gap-6 text-sm text-gray-600">
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 rounded-full border-2 border-green-600" />
          <span>Win</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 rounded-full border-2 border-red-600" />
          <span>Loss</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 rounded-full border-2 border-gray-600" />
          <span>Draw</span>
        </div>
        <span className="text-gray-400">|</span>
        <span className="text-xs text-gray-500">
          Scroll to zoom • Drag to pan • Hover for details
        </span>
      </div>
    </div>
  );
}
