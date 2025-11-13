"use client";

import { useMemo, useState, type ComponentType } from "react";
import {
  Fight,
  FightCardSection as FightCardSectionType,
  isTitleFight,
  isMainEvent,
} from "@/lib/fight-utils";
import EnhancedFightCard from "./EnhancedFightCard";
import {
  ChevronDown,
  ChevronUp,
  Flame,
  Rows3,
  Shuffle,
  Sparkles,
  Zap,
} from "lucide-react";

interface FightCardSectionProps {
  section: FightCardSectionType;
  eventName: string;
  allFights: Fight[];
}

type SortMode = "card" | "result" | "method";

const SECTION_CONFIG: Record<
  FightCardSectionType["section"],
  {
    icon: ComponentType<{ className?: string }>;
    gradient: string;
    border: string;
  }
> = {
  main: {
    icon: Flame,
    gradient: "from-rose-500/20 via-amber-500/10 to-transparent",
    border: "border-rose-400/60",
  },
  prelims: {
    icon: Zap,
    gradient: "from-sky-500/20 via-indigo-500/10 to-transparent",
    border: "border-sky-400/60",
  },
  early_prelims: {
    icon: Sparkles,
    gradient: "from-purple-500/20 via-fuchsia-500/10 to-transparent",
    border: "border-purple-400/60",
  },
};

/**
 * Cinematic, story-driven wrapper for the main/prelim/early cards that
 * adds sorting, sticky headers, and a collapsible fight mini-map.
 */
export default function FightCardSection({
  section,
  eventName,
  allFights,
}: FightCardSectionProps) {
  const [sortMode, setSortMode] = useState<SortMode>("card");
  const [collapsed, setCollapsed] = useState(section.section === "early_prelims");

  const config = SECTION_CONFIG[section.section];
  const Icon = config.icon;

  const sortedFights = useMemo(() => {
    const fights = [...section.fights];
    if (sortMode === "result") {
      return fights.sort((a, b) => (a.result || "zzz").localeCompare(b.result || "zzz"));
    }
    if (sortMode === "method") {
      return fights.sort((a, b) => (a.method || "zzz").localeCompare(b.method || "zzz"));
    }
    return fights;
  }, [section.fights, sortMode]);

  const miniMap = useMemo(
    () =>
      sortedFights.map((fight, index) => ({
        index: index + 1,
        label: `${fight.fighter_1_name.split(" ").pop() ?? fight.fighter_1_name} vs ${fight.fighter_2_name.split(" ").pop() ?? fight.fighter_2_name}`,
        result: fight.result,
      })),
    [sortedFights]
  );

  return (
    <section className="space-y-4">
      <div
        className={`sticky top-20 z-20 rounded-3xl border ${config.border} bg-gradient-to-r ${config.gradient} px-5 py-4 shadow-lg backdrop-blur`}
      >
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3 text-white">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/30 bg-white/10">
              <Icon className="h-6 w-6" aria-hidden />
            </div>
            <div>
              <h3 className="text-xl font-black uppercase tracking-[0.3em]">{section.label}</h3>
              <p className="text-xs text-slate-200/70">{section.fights.length} showcase bouts</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {[
              { key: "card" as SortMode, label: "Card order", icon: Rows3 },
              { key: "result" as SortMode, label: "Result", icon: Shuffle },
              { key: "method" as SortMode, label: "Method", icon: Sparkles },
            ].map((option) => (
              <button
                key={option.key}
                onClick={() => setSortMode(option.key)}
                className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.25em] transition ${
                  sortMode === option.key
                    ? "border-white/60 bg-white/10 text-white"
                    : "border-white/20 text-slate-200 hover:border-white/40 hover:text-white"
                }`}
                type="button"
              >
                <option.icon className="h-3.5 w-3.5" aria-hidden />
                {option.label}
              </button>
            ))}

            <button
              onClick={() => setCollapsed((value) => !value)}
              className="inline-flex items-center gap-2 rounded-full border border-white/20 px-3 py-1 text-xs font-semibold uppercase tracking-[0.25em] text-slate-200 transition hover:border-white/40 hover:text-white"
              type="button"
            >
              {collapsed ? <ChevronDown className="h-3.5 w-3.5" aria-hidden /> : <ChevronUp className="h-3.5 w-3.5" aria-hidden />}
              {collapsed ? "Expand" : "Collapse"}
            </button>
          </div>
        </div>

        {!collapsed && (
          <div className="mt-4 grid gap-2 rounded-2xl border border-white/10 bg-white/5 p-3 text-xs text-slate-200">
            {miniMap.map((item) => (
              <div key={item.index} className="flex items-center gap-3">
                <span className="flex h-6 w-6 items-center justify-center rounded-full border border-white/20 bg-white/10 text-[0.7rem] font-semibold">
                  {item.index}
                </span>
                <span className="flex-1 truncate">{item.label}</span>
                {item.result && <span className="rounded-full bg-white/10 px-2 py-0.5 text-[0.65rem] uppercase tracking-[0.2em]">{item.result}</span>}
              </div>
            ))}
          </div>
        )}
      </div>

      {!collapsed && (
        <div className="grid gap-4 lg:grid-cols-2">
          {sortedFights.map((fight) => {
            const isTitleBout = isTitleFight(fight, eventName);
            const isMain = isMainEvent(fight, allFights, eventName);

            return (
              <EnhancedFightCard
                key={fight.fight_id}
                fight={fight}
                isTitleFight={isTitleBout}
                isMainEvent={isMain}
              />
            );
          })}
        </div>
      )}
    </section>
  );
}
