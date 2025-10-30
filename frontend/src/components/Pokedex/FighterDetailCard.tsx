"use client";

import StatsDisplay from "@/components/StatsDisplay";
import type { FighterDetail } from "@/lib/types";

type Props = {
  fighterId: string;
  fighter: FighterDetail | null;
  isLoading: boolean;
};

export default function FighterDetailCard({ fighterId, fighter, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-6 text-slate-300">
        Loading fighter details...
      </div>
    );
  }

  if (!fighter) {
    return (
      <div className="rounded-lg border border-red-900/80 bg-red-950/30 p-6 text-red-200">
        Fighter with id <code>{fighterId}</code> was not found.
      </div>
    );
  }

  return (
    <article className="space-y-6 rounded-3xl border-4 border-pokedexBlue bg-slate-950/90 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold text-pokedexYellow">{fighter.name}</h1>
        {fighter.nickname && <h2 className="text-lg text-slate-400">"{fighter.nickname}"</h2>}
        <p className="text-sm text-slate-400">{fighter.record ?? "Record unavailable"}</p>
      </header>
      <section className="grid grid-cols-2 gap-4 text-sm text-slate-200 md:grid-cols-4">
        <Info label="Height" value={fighter.height} />
        <Info label="Weight" value={fighter.weight} />
        <Info label="Reach" value={fighter.reach} />
        <Info label="Leg Reach" value={fighter.leg_reach} />
        <Info label="Stance" value={fighter.stance} />
        <Info label="DOB" value={fighter.dob ?? "—"} />
        <Info label="Division" value={fighter.division ?? "—"} />
      </section>

      <StatsDisplay title="Striking" stats={fighter.striking} />
      <StatsDisplay title="Grappling" stats={fighter.grappling} />
      <StatsDisplay title="Significant Strikes" stats={fighter.significant_strikes} />
      <StatsDisplay title="Takedowns" stats={fighter.takedown_stats} />

      <section>
        <h3 className="text-xl font-semibold text-pokedexYellow">Fight History</h3>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-800 text-left text-xs">
            <thead className="bg-slate-900/70 text-slate-400">
              <tr>
                <th className="px-3 py-2">Event</th>
                <th className="px-3 py-2">Date</th>
                <th className="px-3 py-2">Opponent</th>
                <th className="px-3 py-2">Result</th>
                <th className="px-3 py-2">Method</th>
                <th className="px-3 py-2">Round</th>
                <th className="px-3 py-2">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-200">
              {fighter.fight_history.map((fight) => (
                <tr key={fight.fight_id}>
                  <td className="px-3 py-2">{fight.event_name}</td>
                  <td className="px-3 py-2">{fight.event_date ?? "—"}</td>
                  <td className="px-3 py-2">{fight.opponent}</td>
                  <td className="px-3 py-2">{fight.result}</td>
                  <td className="px-3 py-2">{fight.method}</td>
                  <td className="px-3 py-2">{fight.round ?? "—"}</td>
                  <td className="px-3 py-2">{fight.time ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </article>
  );
}

function Info({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="text-sm text-slate-100">{value ?? "—"}</p>
    </div>
  );
}
