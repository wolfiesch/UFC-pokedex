"use client";

import { useEffect, useMemo, useState } from "react";
import { Search, X } from "lucide-react";

interface EventSearchProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export default function EventSearch({
  value,
  onChange,
  placeholder = "Search events...",
  className = "",
}: EventSearchProps) {
  const [localValue, setLocalValue] = useState(value);

  // Memoize the composed container styles so we can add optional width overrides without recomputing them per render.
  const containerClasses = useMemo(() => {
    return [
      "relative",
      "flex-1",
      "overflow-hidden",
      "rounded-full",
      "border",
      "border-white/10",
      "bg-white/10",
      "backdrop-blur",
      className,
    ]
      .filter(Boolean)
      .join(" ");
  }, [className]);

  // Debounce the search input so we only propagate queries after the user pauses typing.
  useEffect(() => {
    const timer = setTimeout(() => {
      onChange(localValue);
    }, 300);

    return () => clearTimeout(timer);
  }, [localValue, onChange]);

  return (
    <div className={containerClasses}>
      <div className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-white/60">
        <Search className="h-4 w-4" aria-hidden="true" />
      </div>
      <input
        type="text"
        value={localValue}
        onChange={(event) => setLocalValue(event.target.value)}
        placeholder={placeholder}
        className="w-full bg-transparent py-3 pl-11 pr-14 text-sm font-medium text-white placeholder:text-white/40 focus:outline-none"
      />
      {localValue && (
        <button
          onClick={() => {
            setLocalValue("");
            onChange("");
          }}
          className="absolute right-3 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full bg-white/10 text-white/70 transition hover:bg-white/20"
          aria-label="Clear search"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
