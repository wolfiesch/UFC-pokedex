"use client";

import type { ReactNode } from "react";

type Props = {
  title: string;
  children: ReactNode;
};

export default function PokedexCard({ title, children }: Props) {
  return (
    <article className="rounded-3xl border-4 border-pokedexBlue bg-slate-950/90 p-6 shadow-[0_0_30px_rgba(42,117,187,0.4)]">
      <header className="mb-4 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-pokedexYellow">{title}</h2>
        <span className="h-4 w-4 rounded-full bg-pokedexRed shadow-[0_0_10px_rgba(227,53,13,0.7)]" />
      </header>
      <div className="space-y-4">{children}</div>
    </article>
  );
}
