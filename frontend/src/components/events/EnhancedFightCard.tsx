"use client";

import {
  Activity,
  ArrowUpRight,
  Award,
  Crown,
  Scale,
  Star,
  User,
} from "lucide-react";
import { Fight, getFightOutcomeColor, parseRecord } from "@/lib/fight-utils";

interface EnhancedFightCardProps {
  fight: Fight;
  isTitleFight?: boolean;
  isMainEvent?: boolean;
  fighterRecord?: string | null; // fighter_1's record from detail page
  featured?: boolean;
}

/**
 * Enhanced fight card component with fighter records, stat strips, and collectible presentation.
 */
export default function EnhancedFightCard({
  fight,
  isTitleFight = false,
  isMainEvent = false,
  fighterRecord,
  featured = false,
}: EnhancedFightCardProps) {
  const outcomeColor = getFightOutcomeColor(fight.result);
  const parsedRecord = fighterRecord ? parseRecord(fighterRecord) : null;

  const fighterBadge = (name: string, seed: number) => {
    const palette = [
      "from-rose-500/60 via-amber-500/40 to-red-500/40",
      "from-sky-500/60 via-cyan-500/40 to-indigo-500/40",
      "from-emerald-500/60 via-lime-500/40 to-teal-500/40",
      "from-purple-500/60 via-fuchsia-500/40 to-indigo-500/40",
    ];
    const gradient = palette[seed % palette.length];

    return (
      <div className={`flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br ${gradient} text-lg font-bold text-white shadow-lg`}> 
        {initials(name)}
      </div>
    );
  };

  const metaBands = [
    {
      label: "Weight",
      value: fight.weight_class ?? "TBD",
      icon: <Scale className="h-3.5 w-3.5" aria-hidden="true" />,
    },
    {
      label: "Method",
      value: fight.method ?? "Announced fight",
      icon: <Activity className="h-3.5 w-3.5" aria-hidden="true" />,
    },
    {
      label: "Finish",
      value: fight.round && fight.time ? `R${fight.round} • ${fight.time}` : "TBD",
      icon: <Award className="h-3.5 w-3.5" aria-hidden="true" />,
    },
  ];

  return (
    <article
      className={`relative overflow-hidden rounded-[30px] border px-6 py-5 transition-all duration-300 hover:-translate-y-1 hover:border-white/40 hover:shadow-[0_35px_80px_-60px_rgba(15,23,42,0.95)] ${
        featured
          ? "border-cyan-400/60 bg-gradient-to-br from-slate-900 via-slate-900/70 to-slate-950"
          : "border-white/10 bg-slate-900/40"
      }`}
    >
      {isTitleFight && (
        <div className="absolute right-4 top-4 flex items-center gap-2 rounded-full border border-amber-400/60 bg-amber-400/20 px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-amber-100">
          <Crown className="h-3.5 w-3.5" aria-hidden="true" /> Title fight
        </div>
      )}
      {isMainEvent && !isTitleFight && (
        <div className="absolute right-4 top-4 flex items-center gap-2 rounded-full border border-rose-400/60 bg-rose-400/20 px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-rose-100">
          <Star className="h-3.5 w-3.5" aria-hidden="true" /> Main event
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-[1.35fr_0.65fr]">
        <div className="flex flex-col gap-5">
          <div className="flex items-center gap-4">
            {fighterBadge(fight.fighter_1_name, fight.fight_id.length)}
            <div className="space-y-1">
              <p className="text-xs uppercase tracking-[0.35em] text-slate-300/70">Red corner</p>
              <h3 className="text-xl font-bold text-white">{fight.fighter_1_name}</h3>
              {parsedRecord && (
                <p className="text-xs text-slate-300/80">Record: {parsedRecord.wins}-{parsedRecord.losses}-{parsedRecord.draws}</p>
              )}
            </div>
            {fight.result && (
              <span className={`ml-auto inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] ${outcomeColor}`}>
                <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" /> {fight.result}
              </span>
            )}
          </div>

          <div className="flex items-center gap-4">
            <div className="h-px flex-1 bg-gradient-to-r from-transparent via-white/20 to-transparent" />
            <span className="text-xs font-semibold uppercase tracking-[0.4em] text-slate-400">VS</span>
            <div className="h-px flex-1 bg-gradient-to-r from-transparent via-white/20 to-transparent" />
          </div>

          <div className="flex items-center gap-4">
            {fighterBadge(fight.fighter_2_name, fight.fight_id.length + 7)}
            <div className="space-y-1">
              <p className="text-xs uppercase tracking-[0.35em] text-slate-300/70">Blue corner</p>
              <h4 className="text-lg font-semibold text-slate-200">{fight.fighter_2_name}</h4>
            </div>
          </div>
        </div>

        <div className="flex flex-col justify-between gap-4 rounded-2xl border border-white/10 bg-white/5 p-4 text-xs text-slate-200 backdrop-blur">
          <div className="flex items-center gap-2 text-[0.65rem] uppercase tracking-[0.35em] text-slate-300/80">
            <User className="h-3.5 w-3.5" aria-hidden="true" /> Tale of the tape
          </div>
          <div className="space-y-2">
            {metaBands.map((band) => (
              <div
                key={band.label}
                className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[0.7rem] font-semibold uppercase tracking-[0.3em]"
              >
                <span className="flex items-center gap-2 text-slate-200">
                  {band.icon}
                  {band.label}
                </span>
                <span className="text-slate-100">{band.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </article>
  );
}

function initials(name: string): string {
  const parts = name.split(" ").filter(Boolean);
  if (parts.length === 0) {
    return "?";
  }

  const letters = parts.slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "");
  return letters.join("");
}
