"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ListTree, Shield, Sparkles, Sword } from "lucide-react";
import { Fight, FightCardSection as FightCardSectionType, isTitleFight, isMainEvent } from "@/lib/fight-utils";
import EnhancedFightCard from "./EnhancedFightCard";

interface FightCardSectionProps {
  section: FightCardSectionType;
  eventName: string;
  allFights: Fight[];
}

/**
 * Cinematic section view that keeps the card order visible while allowing sorting and collapsing.
 */
export default function FightCardSection({
  section,
  eventName,
  allFights,
}: FightCardSectionProps) {
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false);
  const [sortMode, setSortMode] = useState<"order" | "result" | "method">("order");

  const sectionConfig = {
    main: {
      label: section.label,
      accent: "from-rose-500/30 via-orange-500/20 to-amber-500/10",
      icon: <Shield className="h-4 w-4" aria-hidden="true" />,
    },
    prelims: {
      label: section.label,
      accent: "from-sky-500/25 via-indigo-500/20 to-purple-500/10",
      icon: <Sparkles className="h-4 w-4" aria-hidden="true" />,
    },
    early_prelims: {
      label: section.label,
      accent: "from-emerald-500/20 via-teal-500/15 to-cyan-500/10",
      icon: <Sword className="h-4 w-4" aria-hidden="true" />,
    },
  };

  const config = sectionConfig[section.section];

  const sortedFights = useMemo(() => {
    if (sortMode === "order") {
      return section.fights;
    }

    const fightsCopy = [...section.fights];
    if (sortMode === "result") {
      return fightsCopy.sort((a, b) => (a.result || "").localeCompare(b.result || ""));
    }

    return fightsCopy.sort((a, b) => (a.method || "").localeCompare(b.method || ""));
  }, [section.fights, sortMode]);

  return (
    <section className="space-y-4">
      <header className="sticky top-24 z-20">
        <div
          className={`relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-r ${config.accent} px-6 py-5 shadow-[0_30px_80px_-60px_rgba(15,23,42,0.95)] backdrop-blur`}
        >
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-3 text-sm font-semibold uppercase tracking-[0.35em] text-slate-100">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/30 bg-white/10">
                {config.icon}
              </span>
              {config.label}
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-200">
              <ListTree className="h-4 w-4" aria-hidden="true" />
              <span>{section.fights.length} {section.fights.length === 1 ? "fight" : "fights"}</span>
              <button
                type="button"
                onClick={() => setIsCollapsed((previous) => !previous)}
                className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 font-semibold uppercase tracking-[0.3em] text-slate-100 transition hover:border-white/40 hover:bg-white/20"
              >
                Toggle
                <ChevronDown
                  className={`h-4 w-4 transition-transform ${isCollapsed ? "rotate-180" : "rotate-0"}`}
                  aria-hidden="true"
                />
              </button>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.25em] text-slate-200">
            {([
              { id: "order" as const, label: "Card Order" },
              { id: "result" as const, label: "Result" },
              { id: "method" as const, label: "Method" },
            ] satisfies Array<{ id: typeof sortMode; label: string }>).map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setSortMode(tab.id)}
                className={`rounded-full border px-3 py-1.5 transition ${
                  sortMode === tab.id
                    ? "border-cyan-300/70 bg-cyan-400/20 text-cyan-100"
                    : "border-white/20 bg-white/10 text-slate-200 hover:border-white/40 hover:bg-white/20"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="mt-4 flex items-center gap-1 text-[0.65rem] uppercase tracking-[0.6em] text-slate-100/70">
            {section.fights.map((fight) => (
              <span key={fight.fight_id} className="h-1 w-10 rounded-full bg-white/20" aria-hidden="true" />
            ))}
          </div>
        </div>
      </header>

      <div
        className={`grid gap-4 transition-[grid-template-rows,opacity] duration-300 ease-in-out ${
          isCollapsed ? "grid-rows-[0fr] opacity-0" : "grid-rows-[1fr] opacity-100"
        }`}
      >
        <div className="overflow-hidden space-y-4">
          {sortedFights.map((fight, index) => {
            const isTitleBout = isTitleFight(fight, eventName);
            const isMain = isMainEvent(fight, allFights, eventName);

            return (
              <EnhancedFightCard
                key={fight.fight_id}
                fight={fight}
                isTitleFight={isTitleBout}
                isMainEvent={isMain}
                featured={index < 3 && section.section === "main"}
              />
            );
          })}
        </div>
      </div>
    </section>
  );
}
