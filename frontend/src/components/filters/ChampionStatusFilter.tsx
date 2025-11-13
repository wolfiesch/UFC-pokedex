"use client";

type ChampionStatusFilterProps = {
  selectedStatuses: string[];
  onToggleStatus: (status: string) => void;
};

const CHAMPION_STATUS_OPTIONS = [
  { value: "current", label: "Current Champions" },
  { value: "former", label: "Former Champions" },
];

export default function ChampionStatusFilter({
  selectedStatuses,
  onToggleStatus,
}: ChampionStatusFilterProps) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">
        Champion Status
      </label>
      <div className="flex flex-col gap-2">
        {CHAMPION_STATUS_OPTIONS.map((option) => {
          const isChecked = selectedStatuses.includes(option.value);
          return (
            <label
              key={option.value}
              className="flex cursor-pointer items-center gap-2 rounded-lg border border-input bg-background px-4 py-2.5 text-sm text-foreground transition focus-within:ring-2 focus-within:ring-ring hover:bg-accent/50"
            >
              <input
                type="checkbox"
                checked={isChecked}
                onChange={() => onToggleStatus(option.value)}
                className="h-4 w-4 cursor-pointer rounded border-input accent-primary"
              />
              <span>{option.label}</span>
            </label>
          );
        })}
      </div>
    </div>
  );
}
