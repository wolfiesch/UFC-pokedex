"use client";

import { useMemo } from "react";
import { Fight, calculateEventStats } from "@/lib/fight-utils";
import { Activity, BarChart3, Gauge, Target, Timer, TrendingUp } from "lucide-react";

interface EventStatsPanelProps {
  fights: Fight[];
  eventName: string;
}

function buildSparklinePath(values: number[]): string {
  if (values.length === 0) return "";
  const height = 48;
  const width = 160;
  const step = width / Math.max(values.length - 1, 1);

  return values
    .map((value, index) => {
      const x = index * step;
      const y = height - value * height;
      return `${index === 0 ? "M" : "L"}${x},${Math.max(0, Math.min(height, y))}`;
    })
    .join(" ");
}

/**
 * Panel displaying key statistics about an event
 */
export default function EventStatsPanel({ fights, eventName }: EventStatsPanelProps) {
  const stats = calculateEventStats(fights, eventName);

  const finishRate = stats.totalFights > 0 ? stats.finishes / stats.totalFights : 0;
  const decisionRate = stats.totalFights > 0 ? stats.decisions / stats.totalFights : 0;

  const sparklineValues = useMemo(() => {
    if (fights.length === 0) return [] as number[];
    return fights.map((fight) => {
      if (!fight.method) return 0.35;
      const lower = fight.method.toLowerCase();
      if (lower.includes("decision")) {
        return 0.2;
      }
      if (lower.includes("ko") || lower.includes("tko")) {
        return 0.85;
      }
      if (lower.includes("submission")) {
        return 0.7;
      }
      return 0.5;
    });
  }, [fights]);

  const sparklinePath = useMemo(() => buildSparklinePath(sparklineValues), [sparklineValues]);
  const circumference = 2 * Math.PI * 36;
  const finishStroke = circumference * finishRate;
  const decisionStroke = circumference * decisionRate;

  return (
    <div className="space-y-6 rounded-3xl border border-white/10 bg-slate-950/80 p-6 shadow-[0_35px_120px_rgba(15,23,42,0.55)] backdrop-blur-xl">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Event telemetry</p>
          <h3 className="text-lg font-semibold text-white">How the night unfolded</h3>
        </div>
        <div className="inline-flex items-center gap-3 rounded-full border border-emerald-400/30 bg-emerald-500/10 px-4 py-2 text-xs font-semibold text-emerald-100">
          <Gauge className="h-4 w-4" aria-hidden />
          {(finishRate * 100).toFixed(1)}% finish rate
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[220px,1fr]">
        <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-4">
          <svg viewBox="0 0 120 120" className="h-40 w-full">
            <circle
              cx="60"
              cy="60"
              r="36"
              className="stroke-slate-700/40"
              strokeWidth="14"
              fill="none"
            />
            <circle
              cx="60"
              cy="60"
              r="36"
              className="stroke-emerald-400"
              strokeWidth="14"
              fill="none"
              strokeDasharray={`${finishStroke} ${circumference}`}
              strokeDashoffset={circumference * 0.25}
              strokeLinecap="round"
            />
            <circle
              cx="60"
              cy="60"
              r="36"
              className="stroke-sky-400"
              strokeWidth="14"
              fill="none"
              strokeDasharray={`${decisionStroke} ${circumference}`}
              strokeDashoffset={circumference * 0.25 + finishStroke}
              strokeLinecap="round"
            />
            <text
              x="60"
              y="64"
              textAnchor="middle"
              className="fill-white text-2xl font-semibold"
            >
              {stats.totalFights}
            </text>
            <text
              x="60"
              y="84"
              textAnchor="middle"
              className="fill-slate-300 text-xs uppercase tracking-[0.3em]"
            >
              bouts
            </text>
          </svg>
          <div className="mt-3 space-y-2 text-xs text-slate-300">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-400" /> Finishes ({stats.finishes})
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-sky-400" /> Decisions ({stats.decisions})
            </div>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Momentum</p>
                <h4 className="text-base font-semibold text-white">Finish sparkline</h4>
              </div>
              <TrendingUp className="h-4 w-4 text-sky-300" aria-hidden />
            </div>
            <svg viewBox="0 0 160 48" className="mt-4 h-16 w-full">
              <defs>
                <linearGradient id="spark" x1="0" x2="1" y1="0" y2="0">
                  <stop offset="0%" stopColor="rgba(16,185,129,0.4)" />
                  <stop offset="100%" stopColor="rgba(59,130,246,0.45)" />
                </linearGradient>
              </defs>
              <path d={sparklinePath} stroke="url(#spark)" strokeWidth={3} fill="none" strokeLinecap="round" />
            </svg>
            <p className="mt-2 text-xs text-slate-300">
              A glance at how each bout ended—from razor-thin decisions to emphatic stoppages.
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Card layout</p>
                <h4 className="text-base font-semibold text-white">Main vs prelim</h4>
              </div>
              <BarChart3 className="h-4 w-4 text-purple-300" aria-hidden />
            </div>
            <div className="mt-4 space-y-3 text-xs text-slate-200">
              {[{
                label: "Main card",
                value: stats.mainCardFights,
                color: "bg-emerald-400",
              }, {
                label: "Prelims",
                value: stats.prelimFights,
                color: "bg-sky-400",
              }, {
                label: "Title fights",
                value: stats.titleFights,
                color: "bg-amber-400",
              }].map((item) => (
                <div key={item.label}>
                  <div className="flex items-center justify-between">
                    <span>{item.label}</span>
                    <span className="font-semibold text-white">{item.value}</span>
                  </div>
                  <div className="mt-1 h-2 overflow-hidden rounded-full bg-white/10">
                    <div
                      className={`${item.color} h-2 rounded-full`}
                      style={{ width: stats.totalFights ? `${Math.min(100, (item.value / stats.totalFights) * 100)}%` : "0%" }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {stats.weightClassBreakdown.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Weight map</p>
              <h4 className="text-base font-semibold text-white">Distribution of divisions</h4>
            </div>
            <Activity className="h-4 w-4 text-emerald-300" aria-hidden />
          </div>
          <div className="mt-4 space-y-3">
            {stats.weightClassBreakdown.map((division) => (
              <div key={division.name} className="space-y-1">
                <div className="flex items-center justify-between text-xs text-slate-200">
                  <span>{division.name}</span>
                  <span className="font-semibold text-white">{division.fights} bouts</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-2 rounded-full bg-gradient-to-r from-sky-500 via-indigo-500 to-fuchsia-500"
                    style={{ width: `${division.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {(stats.fastestFinish || stats.dominantFinishMethod) && (
        <div className="grid gap-4 sm:grid-cols-2">
          {stats.fastestFinish && (
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Fastest finish</p>
                  <h4 className="text-base font-semibold text-white">{stats.fastestFinish.label}</h4>
                </div>
                <Timer className="h-4 w-4 text-amber-300" aria-hidden />
              </div>
              <p className="mt-3 text-sm text-slate-200">
                Sealed in round {stats.fastestFinish.round ?? "?"} at {stats.fastestFinish.time ?? "N/A"}.
              </p>
            </div>
          )}
          {stats.dominantFinishMethod && (
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Signature outcome</p>
                  <h4 className="text-base font-semibold text-white">{stats.dominantFinishMethod}</h4>
                </div>
                <Target className="h-4 w-4 text-rose-300" aria-hidden />
              </div>
              <p className="mt-3 text-sm text-slate-200">
                The defining technique of the night, delivering the loudest reactions in the arena.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
