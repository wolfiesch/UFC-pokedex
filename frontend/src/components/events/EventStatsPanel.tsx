"use client";

import { Fight, calculateEventStats } from "@/lib/fight-utils";

interface EventStatsPanelProps {
  fights: Fight[];
  eventName: string;
}

/**
 * Panel displaying key statistics about an event
 */
export default function EventStatsPanel({
  fights,
  eventName,
}: EventStatsPanelProps) {
  const stats = calculateEventStats(fights, eventName);

  const statItems = [
    {
      label: "Total Fights",
      value: stats.totalFights,
      icon: "🥊",
      color: "text-blue-400",
    },
    {
      label: "Main Card",
      value: stats.mainCardFights,
      icon: "🔥",
      color: "text-red-400",
    },
    {
      label: "Prelims",
      value: stats.prelimFights,
      icon: "⚡",
      color: "text-yellow-400",
    },
    {
      label: "Title Fights",
      value: stats.titleFights,
      icon: "👑",
      color: "text-amber-400",
    },
    {
      label: "Finishes",
      value: stats.finishes,
      icon: "💥",
      color: "text-green-400",
    },
    {
      label: "Decisions",
      value: stats.decisions,
      icon: "⚖️",
      color: "text-purple-400",
    },
  ];

  const finishRate =
    stats.totalFights > 0
      ? ((stats.finishes / stats.totalFights) * 100).toFixed(1)
      : "0.0";

  return (
    <div className="space-y-4 rounded-lg border border-gray-700 bg-gray-800/50 p-6">
      <div className="flex items-center justify-between border-b border-gray-700 pb-3">
        <h3 className="text-lg font-bold text-white">📊 Event Statistics</h3>
        <span className="rounded-full bg-green-700/30 px-3 py-1 text-sm font-medium text-green-400">
          {finishRate}% Finish Rate
        </span>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {statItems.map((stat) => (
          <div
            key={stat.label}
            className="flex flex-col items-center rounded-lg bg-gray-900/50 p-4 text-center transition-all hover:scale-105 hover:bg-gray-900/70"
          >
            <span className="mb-1 text-2xl">{stat.icon}</span>
            <span className={`text-3xl font-bold ${stat.color}`}>
              {stat.value}
            </span>
            <span className="mt-1 text-xs text-gray-400">{stat.label}</span>
          </div>
        ))}
      </div>

      {/* Weight Classes */}
      {stats.weightClasses.length > 0 && (
        <div className="border-t border-gray-700 pt-4">
          <h4 className="mb-2 text-sm font-medium text-gray-400">
            Weight Classes Represented:
          </h4>
          <div className="flex flex-wrap gap-2">
            {stats.weightClasses.map((weightClass) => (
              <span
                key={weightClass}
                className="rounded-full bg-gray-700 px-3 py-1 text-xs font-medium text-gray-300"
              >
                {weightClass}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
