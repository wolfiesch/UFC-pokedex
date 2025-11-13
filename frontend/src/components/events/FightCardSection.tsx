"use client";

import { useMemo, useState } from "react";
import { Fight, FightCardSection as FightCardSectionType, isTitleFight, isMainEvent } from "@/lib/fight-utils";
import EnhancedFightCard from "./EnhancedFightCard";
import { ChevronDown, ChevronUp, Flame, Sparkles, Zap } from "lucide-react";

interface FightCardSectionProps {
  section: FightCardSectionType;
  eventName: string;
  allFights: Fight[];
}

/**
 * Component for displaying a section of fight card (Main Card, Prelims, Early Prelims)
 */
export default function FightCardSection({
  section,
  eventName,
  allFights,
}: FightCardSectionProps) {
  const [collapsed, setCollapsed] = useState(false);

  const sectionConfig = useMemo(() => ({
    main: {
      icon: Flame,
      gradient: "from-rose-500/20 via-orange-500/15 to-amber-500/10",
      border: "border-rose-500/40",
    },
    prelims: {
      icon: Zap,
      gradient: "from-sky-500/20 via-indigo-500/15 to-blue-500/10",
      border: "border-sky-500/40",
    },
    early_prelims: {
      icon: Sparkles,
      gradient: "from-purple-500/20 via-fuchsia-500/15 to-pink-500/10",
      border: "border-purple-500/40",
    },
  }), []);

  const config = sectionConfig[section.section];
  const Icon = config.icon;

  const fightDots = useMemo(() => {
    if (section.fights.length === 0) return [] as number[];
    return section.fights.map((_, index) => Math.round(((index + 1) / section.fights.length) * 100));
  }, [section.fights]);

  return (
    <div className="space-y-4">
      <header
        className={`sticky top-20 z-30 rounded-3xl border ${config.border} bg-gradient-to-r ${config.gradient} p-5 shadow-lg shadow-black/30 backdrop-blur-xl`}
      >
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3 text-white">
            <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-white/20 bg-white/10">
              <Icon className="h-6 w-6" aria-hidden />
            </span>
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-white/70">Fight chapter</p>
              <h3 className="text-2xl font-semibold tracking-tight">{section.label}</h3>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium text-white">
              {section.fights.length} {section.fights.length === 1 ? "fight" : "fights"}
            </div>
            <div className="flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-[0.35em] text-slate-100">
              Bout order map
            </div>
            <button
              onClick={() => setCollapsed((prev) => !prev)}
              className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-semibold text-white transition-colors hover:border-white/40"
            >
              {collapsed ? <ChevronDown className="h-4 w-4" aria-hidden /> : <ChevronUp className="h-4 w-4" aria-hidden />}
              {collapsed ? "Expand" : "Collapse"}
            </button>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-2">
          {fightDots.map((percentage, index) => (
            <div key={index} className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-white/70" aria-hidden />
              <span className="text-[10px] uppercase tracking-[0.35em] text-white/60">{percentage}%</span>
            </div>
          ))}
        </div>
      </header>

      {!collapsed && (
        <div className="space-y-4">
          {section.fights.map((fight) => {
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
    </div>
  );
}
