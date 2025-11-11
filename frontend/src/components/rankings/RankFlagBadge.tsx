import { cn } from "@/lib/utils";

type RankFlagBadgeProps = {
  currentRank?: number | null;
  peakRank?: number | null;
  isChampion?: boolean;
  isInterimChampion?: boolean;
  className?: string;
};

export function RankFlagBadge({
  currentRank,
  peakRank,
  isChampion,
  isInterimChampion,
  className,
}: RankFlagBadgeProps) {
  const hasCurrentRank =
    typeof currentRank === "number" && Number.isFinite(currentRank);
  const hasPeakRank = typeof peakRank === "number" && Number.isFinite(peakRank);

  if (!hasCurrentRank && !hasPeakRank) {
    return null;
  }

  const championLabel =
    hasCurrentRank && (isChampion || currentRank === 0)
      ? isInterimChampion
        ? "INTERIM"
        : "CHAMP"
      : hasCurrentRank
        ? `#${currentRank}`
        : null;

  return (
    <div
      className={cn(
        "relative inline-flex items-center gap-2 rounded-full bg-black/65 px-3 py-1 text-[11px] font-semibold text-white shadow-[0_8px_24px_rgba(0,0,0,0.45)] ring-1 ring-white/10 backdrop-blur",
        className,
      )}
    >
      <div className="flex items-center gap-2">
        {hasPeakRank && (
          <span className="rounded-full border border-dashed border-amber-200/70 bg-black/40 px-3 py-1 text-[0.65rem] font-semibold tracking-tight text-amber-100">
            Peak {peakRank === 0 ? "C" : `#${peakRank}`}
          </span>
        )}
        {hasCurrentRank && (
          <span className="rounded-full bg-gradient-to-r from-amber-300 to-amber-600 px-3 py-1 text-[0.65rem] font-black uppercase tracking-tight text-black shadow-inner shadow-white/40">
            {championLabel}
          </span>
        )}
      </div>
      <span
        aria-hidden="true"
        className="h-7 w-1 rounded-full bg-gradient-to-b from-amber-300 to-amber-600 shadow-inner shadow-black/30"
      />
    </div>
  );
}
