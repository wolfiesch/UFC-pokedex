"use client";

import { useEffect, useState } from "react";
import { Search, X } from "lucide-react";

interface EventSearchProps {
  /**
   * Current search value controlled by the parent component.
   */
  value: string;
  /**
   * Callback fired when the debounced search term changes.
   */
  onChange: (value: string) => void;
  /**
   * Optional placeholder text to surface contextual hints inside the field.
   */
  placeholder?: string;
  /**
   * Optional className override so the search input can blend into hero/toolbar contexts.
   */
  className?: string;
}

export default function EventSearch({
  value,
  onChange,
  placeholder = "Search events...",
  className,
}: EventSearchProps) {
  const [localValue, setLocalValue] = useState<string>(value);

  // Mirror external value changes (e.g., saved filter preset) into the local input state.
  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  // Debounce the search input to avoid spamming network requests on every keystroke.
  useEffect(() => {
    const timer = setTimeout(() => {
      onChange(localValue);
    }, 300);

    return () => {
      clearTimeout(timer);
    };
  }, [localValue, onChange]);

  return (
    <div className="relative">
      <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4 text-slate-400">
        <Search className="h-4 w-4" aria-hidden="true" />
      </div>
      <input
        type="text"
        value={localValue}
        onChange={(event) => setLocalValue(event.target.value)}
        placeholder={placeholder}
        className={`w-full rounded-full border border-white/10 bg-white/5 pl-12 pr-14 py-3 text-sm text-slate-100 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.05)] backdrop-blur focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-500/60 transition ${className ?? ""}`.trim()}
      />
      {localValue && (
        <button
          onClick={() => {
            setLocalValue("");
            onChange("");
          }}
          className="absolute inset-y-0 right-0 flex items-center pr-4 text-slate-400 transition hover:text-slate-100"
          aria-label="Clear search"
          type="button"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
