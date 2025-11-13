"use client";

import { Flame, Gauge, Sparkles, Trophy } from "lucide-react";
import { Fight, calculateEventStats } from "@/lib/fight-utils";

interface EventStatsPanelProps {
  fights: Fight[];
  eventName: string;
}

/**
 * Cinematic statistics board featuring lightweight visualisations and standout metrics.
 */
export default function EventStatsPanel({ fights, eventName }: EventStatsPanelProps) {
  const stats = calculateEventStats(fights, eventName);

  const finishRate = stats.totalFights > 0 ? stats.finishes / stats.totalFights : 0;
  const decisionRate = stats.totalFights > 0 ? stats.decisions / stats.totalFights : 0;

  const fastestFinish = fights
    .filter((fight) => fight.time && fight.round)
    .map((fight) => ({
      ...fight,
      duration: parseDuration(fight.round!, fight.time!),
    }))
    .sort((a, b) => a.duration - b.duration)[0];

  const weightDistribution = stats.weightClasses.map((weightClass) => {
    const count = fights.filter((fight) => fight.weight_class === weightClass).length;
    return {
      weightClass,
      count,
      percentage: stats.totalFights > 0 ? Math.round((count / stats.totalFights) * 100) : 0,
    };
  });

  return (
    <section className="space-y-6 rounded-[32px] border border-white/10 bg-slate-900/60 p-6 shadow-[0_40px_100px_-70px_rgba(15,23,42,0.95)] backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-lg font-semibold uppercase tracking-[0.35em] text-slate-100">Event statistics</h3>
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/40 bg-cyan-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-cyan-100">
          <Gauge className="h-4 w-4" aria-hidden="true" />
          {(finishRate * 100).toFixed(1)}% finish rate
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Total bouts"
          value={stats.totalFights}
          accent="from-slate-500/30 via-slate-500/10 to-slate-900/60"
          icon={<Sparkles className="h-4 w-4" aria-hidden="true" />}
        />
        <MetricCard
          title="Main card"
          value={stats.mainCardFights}
          accent="from-amber-500/30 via-amber-500/10 to-slate-900/60"
          icon={<Flame className="h-4 w-4" aria-hidden="true" />}
          subtext={`${stats.titleFights} title fights`}
        />
        <MetricCard
          title="Prelims"
          value={stats.prelimFights}
          accent="from-indigo-500/30 via-indigo-500/10 to-slate-900/60"
          icon={<Sparkles className="h-4 w-4" aria-hidden="true" />}
          subtext={`${Math.round(decisionRate * 100)}% decisions`}
        />
        <MetricCard
          title="Finishes"
          value={stats.finishes}
          accent="from-emerald-500/30 via-emerald-500/10 to-slate-900/60"
          icon={<Trophy className="h-4 w-4" aria-hidden="true" />}
          radialFraction={finishRate}
        />
      </div>

      <div className="grid gap-6 md:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
          <h4 className="text-xs font-semibold uppercase tracking-[0.35em] text-slate-300/80">Finish vs decision</h4>
          <div className="mt-4 flex items-center gap-6">
            <div
              className="relative h-32 w-32 rounded-full border border-white/10 bg-slate-900/80"
              style={{
                backgroundImage: `conic-gradient(#34d399 ${finishRate * 360}deg, rgba(148,163,184,0.4) ${finishRate * 360}deg)`
              }}
            >
              <div className="absolute inset-6 flex flex-col items-center justify-center rounded-full bg-slate-950/90">
                <span className="text-lg font-bold text-white">{stats.finishes}</span>
                <span className="text-[0.6rem] uppercase tracking-[0.35em] text-slate-400">Finishes</span>
              </div>
            </div>
            <div className="space-y-2 text-xs uppercase tracking-[0.3em] text-slate-200/80">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-emerald-400" aria-hidden="true" />
                <span>{(finishRate * 100).toFixed(1)}% finishes</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-slate-500" aria-hidden="true" />
                <span>{(decisionRate * 100).toFixed(1)}% decisions</span>
              </div>
            </div>
          </div>
        </div>

        {fastestFinish && (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-xs text-slate-200">
            <h4 className="font-semibold uppercase tracking-[0.35em] text-slate-300/80">Fastest finish</h4>
            <p className="mt-3 text-lg font-bold text-white">{fastestFinish.fighter_1_name} vs {fastestFinish.fighter_2_name}</p>
            <p className="mt-1 text-[0.7rem] uppercase tracking-[0.3em] text-slate-400">{fastestFinish.method ?? "Finish"}</p>
            <p className="mt-4 text-sm text-slate-100">Stopped in {fastestFinish.round} round{fastestFinish.round === 1 ? "" : "s"} at {fastestFinish.time}</p>
          </div>
        )}
      </div>

      {weightDistribution.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-xs text-slate-200">
          <h4 className="font-semibold uppercase tracking-[0.35em] text-slate-300/80">Weight class distribution</h4>
          <div className="mt-3 space-y-2">
            {weightDistribution.map((entry) => (
              <div key={entry.weightClass} className="space-y-1">
                <div className="flex items-center justify-between">
                  <span>{entry.weightClass}</span>
                  <span>{entry.percentage}%</span>
                </div>
                <div className="h-2 rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-blue-500 to-indigo-500"
                    style={{ width: `${entry.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function parseDuration(round: number, time: string): number {
  const [minutes, seconds] = time.split(":").map((value) => parseInt(value, 10));
  const sanitizedSeconds = Number.isFinite(seconds) ? seconds : 0;
  const sanitizedMinutes = Number.isFinite(minutes) ? minutes : 0;
  return (round - 1) * 300 + sanitizedMinutes * 60 + sanitizedSeconds;
}

interface MetricCardProps {
  title: string;
  value: number;
  accent: string;
  icon: JSX.Element;
  subtext?: string;
  radialFraction?: number;
}

function MetricCard({ title, value, accent, icon, subtext, radialFraction }: MetricCardProps) {
  return (
    <div className={`relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br ${accent} p-4 text-slate-100`}>
      <div className="flex items-center justify-between text-xs uppercase tracking-[0.35em] text-slate-200">
        <span className="flex items-center gap-2">{icon}{title}</span>
        {typeof radialFraction === "number" && (
          <span className="text-[0.6rem] text-slate-200/80">{Math.round(radialFraction * 100)}%</span>
        )}
      </div>
      <p className="mt-3 text-3xl font-bold text-white">{value}</p>
      {subtext && <p className="mt-2 text-[0.65rem] uppercase tracking-[0.35em] text-slate-300/80">{subtext}</p>}
    </div>
  );
}
