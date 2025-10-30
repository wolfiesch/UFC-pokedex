"use client";

type StatsDisplayProps = {
  title: string;
  stats: Record<string, string | number | null | undefined>;
};

export default function StatsDisplay({ title, stats }: StatsDisplayProps) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <h3 className="text-lg font-semibold text-pokedexYellow">{title}</h3>
      <dl className="mt-3 grid grid-cols-2 gap-3 text-xs text-slate-300 sm:grid-cols-3">
        {Object.entries(stats).map(([key, value]) => (
          <div key={key}>
            <dt className="font-semibold text-slate-100">{key.replace(/_/g, " ")}</dt>
            <dd>{value ?? "—"}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
