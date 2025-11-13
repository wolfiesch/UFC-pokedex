"use client";

import { ArrowUpAZ, Clock3, TrendingUp } from "lucide-react";

import type { FightWebSortOption } from "@/lib/types";
import { cn } from "@/lib/utils";

import {
  DEFAULT_SORT,
  FIGHT_WEB_SORT_OPTIONS,
} from "./sort-utils";

const SORT_ICONS: Record<FightWebSortOption, React.ComponentType<React.SVGProps<SVGSVGElement>>> = {
  most_active: TrendingUp,
  alphabetical: ArrowUpAZ,
  most_recent: Clock3,
};

type FightWebSortProps = {
  sortBy?: FightWebSortOption | null;
  onChange: (sortBy: FightWebSortOption) => void;
  disabled?: boolean;
};

export function FightWebSort({
  sortBy = DEFAULT_SORT,
  onChange,
  disabled = false,
}: FightWebSortProps) {
  return (
    <aside className="space-y-4 rounded-3xl border border-border/80 bg-card/60 p-6">
      <header className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">
          Sort fighters
        </h2>
        <p className="text-sm text-muted-foreground">
          Change the ordering applied to the loaded graph nodes.
        </p>
      </header>

      <div className="space-y-2">
        {(
          Object.entries(FIGHT_WEB_SORT_OPTIONS) as [
            FightWebSortOption,
            (typeof FIGHT_WEB_SORT_OPTIONS)[FightWebSortOption],
          ][]
        ).map(([key, option]) => {
          const Icon = SORT_ICONS[key];
          const isActive = sortBy === key;
          return (
            <button
              key={key}
              type="button"
              disabled={disabled}
              onClick={() => {
                if (disabled || isActive) {
                  return;
                }
                onChange(key);
              }}
              className={cn(
                "flex w-full items-start gap-3 rounded-2xl border px-4 py-3 text-left transition",
                "bg-background/60 border-border/70 hover:border-foreground/70",
                isActive &&
                  "border-foreground bg-foreground/5 ring-2 ring-foreground/10",
                disabled && "cursor-not-allowed opacity-60 hover:border-border/70",
              )}
              aria-pressed={isActive}
            >
              <Icon className="mt-0.5 h-4 w-4 text-muted-foreground" />
              <div className="flex-1">
                <div className="font-medium text-foreground/90">
                  {option.label}
                </div>
                <div className="text-xs text-muted-foreground">
                  {option.description}
                </div>
              </div>
              {isActive ? (
                <span className="text-xs font-semibold uppercase tracking-[0.25em] text-foreground">
                  Active
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
    </aside>
  );
}
