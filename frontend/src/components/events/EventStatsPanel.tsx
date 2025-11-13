"use client";

import { useMemo, type ComponentType } from "react";
import { Fight, calculateEventStats } from "@/lib/fight-utils";
import { Activity, BarChart3, Gauge, Medal, Timer, TrendingUp } from "lucide-react";

interface EventStatsPanelProps {
  fights: Fight[];
  eventName: string;
}

interface HighlightCard {
  title: string;
  description: string;
  meta: string;
  icon: ComponentType<{ className?: string }>;
}

export default function EventStatsPanel({ fights, eventName }: EventStatsPanelProps) {
  const stats = calculateEventStats(fights, eventName);

  const weightClassCounts = useMemo(() => {
    const counts = new Map<string, number>();
    fights.forEach((fight) => {
      if (fight.weight_class) {
        counts.set(fight.weight_class, (counts.get(fight.weight_class) ?? 0) + 1);
      }
    });
    return Array.from(counts.entries());
  }, [fights]);

  const finishRate = stats.totalFights > 0 ? (stats.finishes / stats.totalFights) * 100 : 0;
  const decisionRate = stats.totalFights > 0 ? (stats.decisions / stats.totalFights) * 100 : 0;

  const fastestFinish = useMemo(() => {
    const finishes = fights.filter((fight) => {
      if (!fight.method || !fight.time || !fight.round) {
        return false;
      }
      const methodLower = fight.method.toLowerCase();
      return !methodLower.includes("decision") && !methodLower.includes("n/a");
    });

    return finishes.reduce<null | { fight: Fight; seconds: number }>((acc, fight) => {
      if (!fight.time || !fight.round) return acc;
      const [minutes, seconds] = fight.time.split(":").map((value) => parseInt(value, 10));
      const totalSeconds = (fight.round - 1) * 300 + minutes * 60 + seconds;
      if (!acc || totalSeconds < acc.seconds) {
        return { fight, seconds: totalSeconds };
      }
      return acc;
    }, null);
  }, [fights]);

  const highlights: HighlightCard[] = useMemo(() => {
    const cards: HighlightCard[] = [];
    if (fastestFinish) {
      cards.push({
        title: "Fastest finish",
        description: `${fastestFinish.fight.fighter_1_name} def. ${fastestFinish.fight.fighter_2_name}`,
        meta: `R${fastestFinish.fight.round} ${fastestFinish.fight.time}`,
        icon: Timer,
      });
    }

    if (stats.titleFights > 0) {
      cards.push({
        title: "Title bouts",
        description: `${stats.titleFights} championship clashes on this card`,
        icon: Medal,
        meta: `${((stats.titleFights / Math.max(stats.totalFights, 1)) * 100).toFixed(0)}% of fights`,
      });
    }

    cards.push({
      title: "Main card pacing",
      description: `${stats.mainCardFights} feature fights headlined the broadcast`,
      icon: TrendingUp,
      meta: `${stats.prelimFights} on the buildup`,
    });

    return cards;
  }, [fastestFinish, stats.titleFights, stats.totalFights, stats.mainCardFights, stats.prelimFights]);

  return (
    <section className="space-y-6 rounded-[32px] border border-white/10 bg-slate-950/80 p-6 shadow-[0_40px_80px_-70px_rgba(15,23,42,0.9)] backdrop-blur">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Event analytics</p>
          <h3 className="text-2xl font-black text-white">How the night unfolded</h3>
        </div>
        <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/50 bg-emerald-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-emerald-100">
          <Gauge className="h-4 w-4" aria-hidden /> {finishRate.toFixed(1)}% finish rate
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <RadialMetric label="Total fights" value={stats.totalFights} percentage={100} accent="#38bdf8" icon={Activity} />
        <RadialMetric label="Finishes" value={stats.finishes} percentage={finishRate} accent="#fbbf24" icon={Gauge} />
        <RadialMetric label="Decisions" value={stats.decisions} percentage={decisionRate} accent="#a855f7" icon={BarChart3} />
        <RadialMetric label="Title fights" value={stats.titleFights} percentage={(stats.titleFights / Math.max(stats.totalFights, 1)) * 100} accent="#34d399" icon={Medal} />
      </div>

      {weightClassCounts.length > 0 && (
        <div className="space-y-3 rounded-3xl border border-white/10 bg-white/5 p-5">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Weight class distribution</p>
          <div className="space-y-3">
            {weightClassCounts.map(([weightClass, count]) => {
              const percentage = (count / Math.max(stats.totalFights, 1)) * 100;
              return (
                <div key={weightClass} className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-slate-300">
                    <span className="uppercase tracking-[0.25em]">{weightClass}</span>
                    <span>{count} bouts</span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
                    <div className="h-full rounded-full bg-gradient-to-r from-sky-400/80 to-indigo-500/80" style={{ width: `${percentage}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        {highlights.map((highlight) => (
          <div key={highlight.title} className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-white/10 via-transparent to-white/5 p-5">
            <highlight.icon className="absolute -top-6 -right-6 h-20 w-20 text-white/10" aria-hidden />
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">{highlight.title}</p>
            <p className="mt-2 text-sm font-semibold text-white">{highlight.description}</p>
            <p className="text-xs text-slate-300">{highlight.meta}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

interface RadialMetricProps {
  label: string;
  value: number;
  percentage: number;
  accent: string;
  icon: ComponentType<{ className?: string }>;
}

function RadialMetric({ label, value, percentage, accent, icon: Icon }: RadialMetricProps) {
  const safePercentage = Math.min(Math.max(percentage, 0), 100);

  return (
    <div className="relative flex flex-col items-center gap-3 rounded-3xl border border-white/10 bg-white/5 p-5 text-center shadow-inner">
      <div className="relative h-28 w-28">
        <div className="absolute inset-0 rounded-full bg-slate-900/60">
          <div
            className="absolute inset-0 rounded-full"
            style={{
              backgroundImage: `conic-gradient(${accent} ${safePercentage * 3.6}deg, rgba(148,163,184,0.15) ${safePercentage * 3.6}deg)`,
            }}
          />
          <div className="absolute inset-[12px] rounded-full border border-white/10 bg-slate-950/90" />
        </div>
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-1">
          <Icon className="h-5 w-5 text-slate-200" aria-hidden />
          <span className="text-2xl font-bold text-white">{value}</span>
          <span className="text-[0.65rem] uppercase tracking-[0.3em] text-slate-400">{label}</span>
        </div>
      </div>
      <span className="text-xs uppercase tracking-[0.3em] text-slate-400">{safePercentage.toFixed(1)}%</span>
    </div>
  );
}
