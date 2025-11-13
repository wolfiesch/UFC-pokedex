"use client";

import { useId, useMemo, useState } from "react";

import type { FightGraphNode } from "@/lib/types";

type FightWebSearchProps = {
  nodes: FightGraphNode[];
  onSelect: (fighterId: string) => void;
  onClear?: () => void;
};

/**
 * Lightweight combobox that filters the currently loaded fighters by name and
 * focuses the graph on the chosen node.
 */
export function FightWebSearch({
  nodes,
  onSelect,
  onClear,
}: FightWebSearchProps) {
  const [query, setQuery] = useState("");
  const datalistId = useId();

  const options = useMemo(() => {
    return nodes.map((node) => ({ id: node.fighter_id, name: node.name }));
  }, [nodes]);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (trimmed.length === 0) {
      return;
    }
    const exactMatch = options.find(
      (option) => option.name.toLowerCase() === trimmed.toLowerCase(),
    );
    if (exactMatch) {
      onSelect(exactMatch.id);
      return;
    }
    const partialMatch = options.find((option) =>
      option.name.toLowerCase().includes(trimmed.toLowerCase()),
    );
    if (partialMatch) {
      onSelect(partialMatch.id);
    }
  };

  const handleClear = () => {
    setQuery("");
    onClear?.();
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-2 rounded-3xl border border-border/80 bg-card/60 p-4"
    >
      <label className="flex flex-col gap-2 text-sm text-muted-foreground">
        <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground/90">
          Focus a fighter
        </span>
        <input
          list={datalistId}
          value={query}
          onChange={(event) => {
            const nextValue = event.target.value;
            setQuery(nextValue);
            const matchingOption = options.find(
              (option) => option.name.toLowerCase() === nextValue.toLowerCase(),
            );
            if (matchingOption) {
              onSelect(matchingOption.id);
            }
          }}
          placeholder="Search within the loaded fighters"
          className="w-full rounded-2xl border border-border bg-background px-3 py-2 text-sm text-foreground shadow-sm outline-none transition focus:border-foreground focus:ring-2 focus:ring-foreground/20"
        />
        <datalist id={datalistId}>
          {options.slice(0, 50).map((option) => (
            <option key={option.id} value={option.name} />
          ))}
        </datalist>
      </label>

      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <button
          type="submit"
          className="inline-flex items-center justify-center rounded-full bg-foreground px-3 py-1 font-semibold text-background transition hover:bg-foreground/90"
        >
          Focus
        </button>
        <button
          type="button"
          onClick={handleClear}
          className="inline-flex items-center justify-center rounded-full border border-border px-3 py-1 font-semibold text-muted-foreground transition hover:border-foreground hover:text-foreground"
        >
          Clear
        </button>
        <span className="ml-auto">{options.length} fighters loaded</span>
      </div>
    </form>
  );
}
