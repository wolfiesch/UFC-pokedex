"use client";

import { Fight, getFightOutcomeColor, parseRecord } from "@/lib/fight-utils";
import {
  Activity,
  ArrowUpRight,
  Clock3,
  Swords,
  Trophy,
  Weight,
} from "lucide-react";

interface EnhancedFightCardProps {
  fight: Fight;
  isTitleFight?: boolean;
  isMainEvent?: boolean;
  fighterRecord?: string | null;
}

const badgeStyle = "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.3em]";

export default function EnhancedFightCard({
  fight,
  isTitleFight = false,
  isMainEvent = false,
  fighterRecord,
}: EnhancedFightCardProps) {
  const outcomeColor = getFightOutcomeColor(fight.result);
  const parsedRecord = fighterRecord ? parseRecord(fighterRecord) : null;

  return (
    <article className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-slate-900/70 via-slate-950/70 to-slate-950/90 p-6 shadow-[0_40px_80px_-60px_rgba(15,23,42,0.8)] transition hover:-translate-y-1 hover:border-white/30 hover:shadow-[0_50px_90px_-60px_rgba(59,130,246,0.45)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(94,234,212,0.12),_transparent_60%)]" />
      <div className="relative z-10 flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            {isTitleFight && (
              <span className={`${badgeStyle} border-amber-400/60 bg-amber-500/15 text-amber-100`}>
                <Trophy className="h-3.5 w-3.5" aria-hidden /> Title bout
              </span>
            )}
            {isMainEvent && !isTitleFight && (
              <span className={`${badgeStyle} border-sky-400/60 bg-sky-500/15 text-sky-100`}>
                <Activity className="h-3.5 w-3.5" aria-hidden /> Main event
              </span>
            )}
          </div>
          {fight.result && (
            <span className={`inline-flex items-center gap-2 rounded-full px-4 py-1 text-xs font-semibold uppercase tracking-[0.35em] ${outcomeColor}`}>
              <ArrowUpRight className="h-3.5 w-3.5" aria-hidden /> {fight.result}
            </span>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="relative flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 flex-shrink-0 rounded-2xl border border-white/20 bg-gradient-to-br from-white/30 to-transparent shadow-inner" />
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Blue corner</p>
                <p className="text-lg font-semibold text-white">{fight.fighter_1_name}</p>
              </div>
            </div>
            {parsedRecord && (
              <div className="flex items-center gap-3 text-xs text-slate-300">
                <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1">
                  <Swords className="h-3 w-3" aria-hidden />
                  {parsedRecord.wins}-{parsedRecord.losses}-{parsedRecord.draws}
                </span>
              </div>
            )}
          </div>

          <div className="relative flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 flex-shrink-0 rounded-2xl border border-white/20 bg-gradient-to-br from-white/30 to-transparent shadow-inner" />
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Red corner</p>
                <p className="text-lg font-semibold text-white">{fight.fighter_2_name}</p>
              </div>
            </div>
            <div className="text-xs text-slate-300">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1">
                <Swords className="h-3 w-3" aria-hidden /> Tale of the tape
              </span>
            </div>
          </div>
        </div>

        <div className="grid gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-xs text-slate-200">
          {fight.weight_class && (
            <div className="flex items-center gap-2">
              <Weight className="h-3.5 w-3.5" aria-hidden />
              <span className="uppercase tracking-[0.25em]">{fight.weight_class}</span>
            </div>
          )}
          {fight.method && (
            <div className="flex items-center gap-2">
              <Swords className="h-3.5 w-3.5" aria-hidden />
              <span>{fight.method}</span>
            </div>
          )}
          {fight.round && fight.time && (
            <div className="flex items-center gap-2">
              <Clock3 className="h-3.5 w-3.5" aria-hidden />
              <span>
                Round {fight.round} · {fight.time}
              </span>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
