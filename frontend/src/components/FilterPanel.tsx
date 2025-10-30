"use client";

import type { ChangeEvent } from "react";

type FilterPanelProps = {
  stances: string[];
  selectedStance: string | null;
  onStanceChange: (stance: string | null) => void;
};

export default function FilterPanel({ stances, selectedStance, onStanceChange }: FilterPanelProps) {
  const handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    onStanceChange(value === "all" ? null : value);
  };

  return (
    <div className="flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-900 px-4 py-3 text-sm text-slate-200">
      <label htmlFor="stance-filter" className="font-semibold">
        Stance
      </label>
      <select
        id="stance-filter"
        value={selectedStance ?? "all"}
        onChange={handleChange}
        className="rounded-md border border-slate-700 bg-slate-950 px-3 py-1 text-sm"
      >
        <option value="all">All</option>
        {stances.map((stance) => (
          <option key={stance} value={stance}>
            {stance}
          </option>
        ))}
      </select>
    </div>
  );
}
