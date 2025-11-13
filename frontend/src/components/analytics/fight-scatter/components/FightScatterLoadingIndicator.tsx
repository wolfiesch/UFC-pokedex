"use client";

export interface FightScatterLoadingIndicatorProps {
  /** Whether the loading overlay should be visible. */
  visible: boolean;
}

/**
 * Small centered overlay shown while opponent headshots preload into cache.
 */
export function FightScatterLoadingIndicator({
  visible,
}: FightScatterLoadingIndicatorProps) {
  if (!visible) {
    return null;
  }

  return (
    <div className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-lg bg-gray-900/90 px-4 py-2 text-sm text-white">
      Loading images...
    </div>
  );
}
