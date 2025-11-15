"use client";

import { memo } from "react";
import type { Streak } from "@/lib/fighter-utils";

interface StreakBadgeProps {
  streak: Streak | null;
  className?: string;
}

/**
 * StreakBadge component displays a pill-style badge for win/loss streaks
 *
 * Visual design:
 * - Win Streak (≥2): 🔥 + count + "W" with green text
 * - Loss Streak (≥2): ❄️ + count + "L" with red text
 * - Pill style with transparent background and subtle border
 * - Only shows for streaks of 2 or more
 *
 * Example: 🔥 3W (3-fight win streak)
 *          ❄️ 2L (2-fight loss streak)
 */
function StreakBadgeComponent({ streak, className = "" }: StreakBadgeProps) {
  // Only show for streaks of 2 or more
  if (!streak || streak.count < 2 || streak.type === "none") {
    return null;
  }

  const getStreakConfig = () => {
    switch (streak.type) {
      case "win":
        return {
          emoji: "🔥",
          suffix: "W",
          textColor: "text-green-500",
          bgColor: "bg-green-500/10",
          borderColor: "border-green-500/20",
        };
      case "loss":
        return {
          emoji: "❄️",
          suffix: "L",
          textColor: "text-red-500",
          bgColor: "bg-red-500/10",
          borderColor: "border-red-500/20",
        };
      case "draw":
        return {
          emoji: "⚫",
          suffix: "D",
          textColor: "text-gray-500",
          bgColor: "bg-gray-500/10",
          borderColor: "border-gray-500/20",
        };
      default:
        return null;
    }
  };

  const config = getStreakConfig();
  if (!config) return null;

  return (
    <div
      className={`inline-flex items-center gap-1 rounded-lg border px-2 py-1 ${config.bgColor} ${config.borderColor} ${className}`}
      role="status"
      aria-label={`${streak.count} ${streak.type} streak`}
    >
      <span className="text-xs leading-none">{config.emoji}</span>
      <span className={`text-xs font-bold leading-none ${config.textColor}`}>
        {streak.count}
        {config.suffix}
      </span>
    </div>
  );
}

export const StreakBadge = memo(StreakBadgeComponent);
