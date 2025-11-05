"use client";

import { Minus, Plus } from "lucide-react";

interface StreakCounterProps {
  label: string;
  count: number | null;
  isDisabled: boolean;
  onIncrement: () => void;
  onDecrement: () => void;
}

export function StreakCounter({
  label,
  count,
  isDisabled,
  onIncrement,
  onDecrement,
}: StreakCounterProps) {
  const displayValue = count === null ? "-" : count;
  const canDecrement = count !== null && count > 0;

  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs font-semibold uppercase tracking-[0.3em] text-foreground/70">
        {label}
      </label>
      <div
        className={`flex items-center gap-2 transition-opacity ${
          isDisabled ? "pointer-events-none opacity-50" : "opacity-100"
        }`}
      >
        {/* Minus button */}
        <button
          type="button"
          onClick={onDecrement}
          disabled={isDisabled || !canDecrement}
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-input bg-background text-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="Decrease streak count"
        >
          <Minus className="h-4 w-4" />
        </button>

        {/* Count display */}
        <div className="flex h-10 w-16 items-center justify-center rounded-xl border border-input bg-background px-3 text-sm font-medium">
          {displayValue}
        </div>

        {/* Plus button */}
        <button
          type="button"
          onClick={onIncrement}
          disabled={isDisabled}
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-input bg-background text-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="Increase streak count"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
