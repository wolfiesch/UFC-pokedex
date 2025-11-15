"use client";

import { memo, useState } from "react";

/**
 * Represents a single fight result for the form bar visualization
 */
export interface FormDataPoint {
  result: "win" | "loss" | "draw" | "nc";
  opponent: string;
  date: string | null;
  method?: string;
}

interface FormBarProps {
  formData: FormDataPoint[];
  className?: string;
}

/**
 * FormBar component displays the last 5 fight results as colored squares
 *
 * Visual design:
 * - Win: Green (#4ADE80)
 * - Loss: Red (#EF4444)
 * - Draw/NC: Gray (#9CA3AF)
 * - 8×8px squares with 3px border radius
 * - 4px gap between squares
 * - Tooltips on hover showing opponent + result
 *
 * Example: 🟩🟩🟥🟩🟩 (3W-1L-1W streak)
 */
function FormBarComponent({ formData, className = "" }: FormBarProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  if (!formData || formData.length === 0) {
    return null;
  }

  // Take only the last 5 fights, reverse to show oldest→newest (left→right)
  const last5Fights = formData.slice(0, 5).reverse();

  const getResultColor = (result: FormDataPoint["result"]) => {
    switch (result) {
      case "win":
        return "bg-green-400 hover:bg-green-500";
      case "loss":
        return "bg-red-500 hover:bg-red-600";
      case "draw":
      case "nc":
        return "bg-gray-400 hover:bg-gray-500";
      default:
        return "bg-gray-400 hover:bg-gray-500";
    }
  };

  const getResultLabel = (result: FormDataPoint["result"]) => {
    switch (result) {
      case "win":
        return "W";
      case "loss":
        return "L";
      case "draw":
        return "D";
      case "nc":
        return "NC";
      default:
        return "?";
    }
  };

  const formatDate = (date: string | null) => {
    if (!date) return "";
    try {
      return new Date(date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return "";
    }
  };

  return (
    <div className={`flex items-center gap-1 ${className}`} data-testid="form-bar">
      {last5Fights.map((fight, index) => (
        <div
          key={`${fight.opponent}-${fight.date}-${index}`}
          className={`relative h-2 w-2 rounded-sm transition-all duration-200 ${getResultColor(
            fight.result,
          )}`}
          role="img"
          aria-label={`${getResultLabel(fight.result)} vs ${fight.opponent}`}
          data-testid={`form-square-${index}`}
          onMouseEnter={() => setHoveredIndex(index)}
          onMouseLeave={() => setHoveredIndex(null)}
        >
          {/* Tooltip - only show when this specific square is hovered */}
          {hoveredIndex === index && (
            <div
              className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 whitespace-nowrap rounded-lg bg-black/90 px-3 py-2 text-xs text-white shadow-lg"
              data-testid={`form-tooltip-${index}`}
            >
              <div className="font-semibold">
                {getResultLabel(fight.result)} vs {fight.opponent}
              </div>
              {fight.method && (
                <div className="text-white/70">{fight.method}</div>
              )}
              {fight.date && (
                <div className="text-white/60">{formatDate(fight.date)}</div>
              )}
              {/* Tooltip arrow */}
              <div className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-black/90" />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export const FormBar = memo(FormBarComponent);
