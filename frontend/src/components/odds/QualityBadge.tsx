"use client";

import { Badge } from "@/components/ui/badge";
import type { OddsQualityTier } from "@/types/odds";
import { cn } from "@/lib/utils";

const QUALITY_STYLES: Record<OddsQualityTier, string> = {
  excellent: "bg-emerald-600/90 text-white border-transparent",
  good: "bg-emerald-500/15 text-emerald-600 border-emerald-600/30 dark:text-emerald-300",
  usable: "bg-blue-500/15 text-blue-600 border-blue-600/30 dark:text-blue-300",
  poor: "bg-amber-500/15 text-amber-600 border-amber-600/30 dark:text-amber-300",
  no_data: "bg-muted text-muted-foreground border-transparent",
};

const QUALITY_LABELS: Record<OddsQualityTier, string> = {
  excellent: "Excellent",
  good: "Good",
  usable: "Usable",
  poor: "Poor",
  no_data: "No Data",
};

export function QualityBadge({ tier }: { tier: OddsQualityTier }) {
  const style = QUALITY_STYLES[tier] ?? QUALITY_STYLES.no_data;
  return (
    <Badge
      variant="outline"
      className={cn(
        "px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.2em]",
        style,
      )}
    >
      {QUALITY_LABELS[tier] ?? tier}
    </Badge>
  );
}
