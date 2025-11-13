"use client";

import { useEffect, useState } from "react";
import { Search, X } from "lucide-react";

interface EventSearchProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export default function EventSearch({ value, onChange, placeholder = "Search events..." }: EventSearchProps) {
  const [localValue, setLocalValue] = useState(value);

  // Debounce the search input so typing feels responsive while still avoiding rapid API calls.
  useEffect(() => {
    const timer = setTimeout(() => {
      onChange(localValue);
    }, 300);

    return () => clearTimeout(timer);
  }, [localValue, onChange]);

  return (
    <div className="relative">
      <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-gray-500">
        <Search className="h-4 w-4" aria-hidden />
      </div>
      <input
        type="text"
        value={localValue}
        onChange={(event) => setLocalValue(event.target.value)}
        placeholder={placeholder}
        className="w-full rounded-xl border border-white/10 bg-white/5 pl-10 pr-12 py-3 text-sm text-white placeholder:text-gray-400 shadow-inner transition focus:border-blue-500/60 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
      />
      {localValue && (
        <button
          onClick={() => {
            setLocalValue("");
            onChange("");
          }}
          className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 transition hover:text-white"
          aria-label="Clear search"
          type="button"
        >
          <X className="h-4 w-4" aria-hidden />
        </button>
      )}
    </div>
  );
}
