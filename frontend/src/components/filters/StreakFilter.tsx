"use client";

import { StreakCounter } from "./StreakCounter";

interface StreakFilterProps {
  winStreakCount: number | null;
  lossStreakCount: number | null;
  onWinStreakChange: (count: number | null) => void;
  onLossStreakChange: (count: number | null) => void;
}

export function StreakFilter({
  winStreakCount,
  lossStreakCount,
  onWinStreakChange,
  onLossStreakChange,
}: StreakFilterProps) {
  const handleWinIncrement = () => {
    onWinStreakChange(winStreakCount === null ? 1 : winStreakCount + 1);
  };

  const handleWinDecrement = () => {
    if (winStreakCount === null || winStreakCount <= 0) return;
    onWinStreakChange(winStreakCount === 1 ? null : winStreakCount - 1);
  };

  const handleLossIncrement = () => {
    onLossStreakChange(lossStreakCount === null ? 1 : lossStreakCount + 1);
  };

  const handleLossDecrement = () => {
    if (lossStreakCount === null || lossStreakCount <= 0) return;
    onLossStreakChange(lossStreakCount === 1 ? null : lossStreakCount - 1);
  };

  // Determine disabled state based on mutual exclusivity
  const isWinDisabled = lossStreakCount !== null;
  const isLossDisabled = winStreakCount !== null;

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:gap-4">
      <StreakCounter
        label="Win Streak"
        count={winStreakCount}
        isDisabled={isWinDisabled}
        onIncrement={handleWinIncrement}
        onDecrement={handleWinDecrement}
      />
      <StreakCounter
        label="Loss Streak"
        count={lossStreakCount}
        isDisabled={isLossDisabled}
        onIncrement={handleLossIncrement}
        onDecrement={handleLossDecrement}
      />
    </div>
  );
}
