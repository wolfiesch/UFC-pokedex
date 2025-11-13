"use client";

import { useEffect, useState } from "react";

import type { FightGraphQueryParams } from "@/types/fight-graph";

const DIVISIONS: readonly string[] = [
  "Flyweight",
  "Bantamweight",
  "Featherweight",
  "Lightweight",
  "Welterweight",
  "Middleweight",
  "Light Heavyweight",
  "Heavyweight",
  "Strawweight",
  "Super Heavyweight",
];

export interface FightGraphControlsProps {
  /** Currently applied query parameters. */
  params: FightGraphQueryParams;
  /** Callback invoked whenever the form submits a new filter set. */
  onSubmit: (nextParams: FightGraphQueryParams) => void;
  /** Whether the parent component is awaiting a network response. */
  isLoading?: boolean;
}

/**
 * Form-based control panel that mirrors the original HTML prototype.
 * The component keeps a local working copy of the filters so users can
 * stage multiple changes before triggering a re-query.
 */
export function FightGraphControls({
  params,
  onSubmit,
  isLoading = false,
}: FightGraphControlsProps) {
  const [formState, setFormState] = useState<FightGraphQueryParams>(params);

  useEffect(() => {
    setFormState(params);
  }, [params]);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit(formState);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex h-full flex-col gap-6 overflow-y-auto rounded-3xl border border-slate-800/60 bg-slate-950/60 p-6 shadow-xl"
    >
      <header className="space-y-1">
        <h2 className="text-sm font-semibold uppercase tracking-[0.4em] text-slate-400">
          Configure
        </h2>
        <p className="text-sm text-slate-300/80">
          Adjust the query to focus on specific weight divisions, time ranges,
          or rivalry counts.
        </p>
      </header>

      <fieldset className="space-y-4 rounded-2xl border border-slate-800/70 bg-slate-900/40 p-5">
        <legend className="px-2 text-xs uppercase tracking-[0.3em] text-cyan-300">
          Weight Class
        </legend>
        <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
          Division
          <select
            value={formState.division ?? ""}
            onChange={(event) => {
              const value = event.target.value.trim();
              setFormState((previous) => ({
                ...previous,
                division: value.length === 0 ? undefined : value,
              }));
            }}
            className="rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm font-medium text-slate-100 shadow-inner focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            <option value="">All divisions</option>
            {DIVISIONS.map((division) => (
              <option key={division} value={division}>
                {division}
              </option>
            ))}
          </select>
        </label>
      </fieldset>

      <fieldset className="space-y-4 rounded-2xl border border-slate-800/70 bg-slate-900/40 p-5">
        <legend className="px-2 text-xs uppercase tracking-[0.3em] text-cyan-300">
          Time Horizon
        </legend>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
            Start Year
            <input
              type="number"
              min={1993}
              max={new Date().getFullYear()}
              value={formState.startYear ?? ""}
              onChange={(event) => {
                const value = event.target.value;
                setFormState((previous) => ({
                  ...previous,
                  startYear: value ? Number.parseInt(value, 10) : undefined,
                }));
              }}
              className="rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm font-semibold text-slate-100 shadow-inner focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            />
          </label>
          <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
            End Year
            <input
              type="number"
              min={1993}
              max={new Date().getFullYear()}
              value={formState.endYear ?? ""}
              onChange={(event) => {
                const value = event.target.value;
                setFormState((previous) => ({
                  ...previous,
                  endYear: value ? Number.parseInt(value, 10) : undefined,
                }));
              }}
              className="rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm font-semibold text-slate-100 shadow-inner focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="space-y-4 rounded-2xl border border-slate-800/70 bg-slate-900/40 p-5">
        <legend className="px-2 text-xs uppercase tracking-[0.3em] text-cyan-300">
          Density
        </legend>
        <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
          Fight Limit
          <input
            type="number"
            min={20}
            max={400}
            step={10}
            value={formState.limit ?? 200}
            onChange={(event) => {
              const value = event.target.value;
              setFormState((previous) => ({
                ...previous,
                limit: value ? Number.parseInt(value, 10) : undefined,
              }));
            }}
            className="rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm font-semibold text-slate-100 shadow-inner focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          />
        </label>
        <label className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border border-slate-700 bg-slate-900 text-cyan-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            checked={Boolean(formState.includeUpcoming)}
            onChange={(event) => {
              const { checked } = event.target;
              setFormState((previous) => ({
                ...previous,
                includeUpcoming: checked,
              }));
            }}
          />
          Include upcoming fights
        </label>
      </fieldset>

      <button
        type="submit"
        className="mt-auto flex items-center justify-center gap-2 rounded-2xl border border-cyan-400/30 bg-gradient-to-r from-cyan-500/30 via-fuchsia-500/20 to-cyan-500/30 px-6 py-3 text-sm font-bold uppercase tracking-[0.4em] text-slate-100 transition hover:from-cyan-500/40 hover:to-fuchsia-500/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
        disabled={isLoading}
      >
        {isLoading ? "Loading..." : "Refresh Graph"}
      </button>
    </form>
  );
}
