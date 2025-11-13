"use client";

import { useState, useEffect } from "react";
import { Search, X } from "lucide-react";

interface EventSearchProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export default function EventSearch({ value, onChange, placeholder = "Search events..." }: EventSearchProps) {
  const [localValue, setLocalValue] = useState(value);

  // Debounce the search input
  useEffect(() => {
    const timer = setTimeout(() => {
      onChange(localValue);
    }, 300);

    return () => clearTimeout(timer);
  }, [localValue, onChange]);

  return (
    <div className="relative">
      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        <Search className="h-4 w-4 text-slate-400" aria-hidden />
      </div>
      <input
        type="text"
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        placeholder={placeholder}
        className="w-full pl-10 pr-12 py-3 rounded-xl border border-slate-700/60 bg-slate-900/70 text-white placeholder-slate-500 shadow-inner shadow-black/20 backdrop-blur focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition-all"
      />
      {localValue && (
        <button
          onClick={() => {
            setLocalValue("");
            onChange("");
          }}
          className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-200 transition-colors"
          aria-label="Clear search"
        >
          <X className="h-4 w-4" aria-hidden />
        </button>
      )}
    </div>
  );
}
