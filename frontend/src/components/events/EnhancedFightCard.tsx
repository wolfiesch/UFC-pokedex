"use client";

import { useMemo, useState } from "react";
import { Fight, getFightOutcomeColor, parseRecord } from "@/lib/fight-utils";
import {
  ArrowRight,
  BadgeCheck,
  Flame,
  Medal,
  ShieldCheck,
  Sword,
  Timer,
} from "lucide-react";

interface EnhancedFightCardProps {
  fight: Fight;
  isTitleFight?: boolean;
  isMainEvent?: boolean;
  fighterRecord?: string | null; // fighter_1's record from detail page
}

/**
 * Enhanced fight card component with fighter records and visual styling
 */
export default function EnhancedFightCard({
  fight,
  isTitleFight = false,
  isMainEvent = false,
  fighterRecord,
}: EnhancedFightCardProps) {
  const [detailTab, setDetailTab] = useState<"result" | "method">("result");
  const outcomeColor = getFightOutcomeColor(fight.result);
  const parsedRecord = fighterRecord ? parseRecord(fighterRecord) : null;

  const premiumStrip = isTitleFight || isMainEvent;

  const detailSummary = useMemo(() => {
    if (detailTab === "result") {
      return fight.result ? `${fight.result} · ${fight.method ?? "Method TBA"}` : "Awaiting official decision";
    }
    if (fight.method) {
      return `${fight.method}${fight.round ? ` · Round ${fight.round}` : ""}${fight.time ? ` · ${fight.time}` : ""}`;
    }
    return "Method pending";
  }, [detailTab, fight.method, fight.result, fight.round, fight.time]);

  return (
    <div
      className={`relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/80 p-6 shadow-[0_25px_90px_rgba(15,23,42,0.45)] transition-all duration-300 hover:-translate-y-1 hover:border-white/20`}
    >
      <div className="absolute inset-0 opacity-30" style={{
        backgroundImage:
          "radial-gradient(circle at 20% 20%, rgba(255,255,255,0.12), transparent 55%), radial-gradient(circle at 80% 0%, rgba(59,130,246,0.12), transparent 50%), linear-gradient(135deg, rgba(15,23,42,0.6) 0%, rgba(2,6,23,0.8) 100%)",
      }} aria-hidden />

      {(isTitleFight || isMainEvent) && (
        <div className="absolute -top-3 left-6 flex gap-2">
          {isTitleFight && (
            <span className="inline-flex items-center gap-2 rounded-full border border-amber-400/70 bg-amber-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-amber-100 shadow-lg shadow-amber-500/20">
              <ShieldCheck className="h-4 w-4" aria-hidden /> Title Bout
            </span>
          )}
          {isMainEvent && (
            <span className="inline-flex items-center gap-2 rounded-full border border-rose-400/70 bg-rose-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-rose-100 shadow-lg shadow-rose-500/20">
              <Flame className="h-4 w-4" aria-hidden /> Main Event
            </span>
          )}
        </div>
      )}

      <div className="relative grid gap-6 lg:grid-cols-[1.1fr,0.9fr]">
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 sm:items-center sm:gap-6">
            <div className="flex items-center gap-4">
              <div className="h-14 w-14 overflow-hidden rounded-2xl border border-white/20 bg-gradient-to-br from-slate-700 via-slate-900 to-black" aria-hidden>
                <div className="flex h-full items-center justify-center text-lg font-semibold text-white/80">
                  {fight.fighter_1_name.charAt(0)}
                </div>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Red corner</p>
                <h4 className="text-lg font-semibold text-white">{fight.fighter_1_name}</h4>
                {parsedRecord && (
                  <p className="text-xs text-slate-300">Record {parsedRecord.wins}-{parsedRecord.losses}-{parsedRecord.draws}</p>
                )}
              </div>
            </div>

            <div className="flex items-center justify-end gap-4">
              <div className="text-right">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Blue corner</p>
                <h4 className="text-lg font-semibold text-white">{fight.fighter_2_name}</h4>
              </div>
              <div className="h-14 w-14 overflow-hidden rounded-2xl border border-white/20 bg-gradient-to-br from-slate-700 via-slate-900 to-black" aria-hidden>
                <div className="flex h-full items-center justify-center text-lg font-semibold text-white/80">
                  {fight.fighter_2_name.charAt(0)}
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-center gap-3 text-xs uppercase tracking-[0.3em] text-slate-400">
            <span className="h-px w-10 bg-gradient-to-r from-transparent via-slate-600 to-transparent" aria-hidden />
            VS
            <span className="h-px w-10 bg-gradient-to-r from-transparent via-slate-600 to-transparent" aria-hidden />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 p-1 text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-200">
              {(["result", "method"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setDetailTab(tab)}
                  className={`rounded-full px-3 py-1 transition-all ${
                    detailTab === tab
                      ? "bg-white/20 text-white shadow-[0_0_18px_rgba(148,163,184,0.45)]"
                      : "text-slate-300"
                  }`}
                >
                  {tab === "result" ? "Result" : "Method"}
                </button>
              ))}
            </div>

            {fight.result && (
              <span
                className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] ${outcomeColor}`}
              >
                <BadgeCheck className="h-4 w-4" aria-hidden /> {fight.result}
              </span>
            )}
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
            {detailSummary}
          </div>
        </div>

        <div className="space-y-4">
          {premiumStrip && (
            <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-sky-500/15 via-purple-500/10 to-pink-500/10 p-4 text-xs text-slate-200">
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.35em] text-slate-300">
                <Medal className="h-4 w-4 text-amber-300" aria-hidden /> Spotlight match-up
              </div>
              <div className="mt-3 grid gap-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-2 text-slate-200">
                    <Sword className="h-4 w-4 text-slate-300" aria-hidden /> Weight class
                  </span>
                  <span className="font-semibold text-white">{fight.weight_class ?? "TBD"}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-2 text-slate-200">
                    <Timer className="h-4 w-4 text-slate-300" aria-hidden /> Scheduled rounds
                  </span>
                  <span className="font-semibold text-white">{fight.round ?? "—"}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-2 text-slate-200">
                    <ArrowRight className="h-4 w-4 text-slate-300" aria-hidden /> Official time
                  </span>
                  <span className="font-semibold text-white">{fight.time ?? "Pending"}</span>
                </div>
              </div>
            </div>
          )}

          <div className="grid gap-3 text-xs text-slate-300">
            <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 p-3">
              <span className="inline-flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-emerald-300" aria-hidden />
                Weight class
              </span>
              <span className="text-white">{fight.weight_class ?? "TBA"}</span>
            </div>
            {fight.method && (
              <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 p-3">
                <span className="inline-flex items-center gap-2">
                  <Sword className="h-4 w-4 text-rose-300" aria-hidden />
                  Method
                </span>
                <span className="text-white">{fight.method}</span>
              </div>
            )}
            {fight.round && fight.time && (
              <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 p-3">
                <span className="inline-flex items-center gap-2">
                  <Timer className="h-4 w-4 text-sky-300" aria-hidden />
                  Time
                </span>
                <span className="text-white">R{fight.round} · {fight.time}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
