"use client";

import { useState, useEffect } from "react";

interface EventSearchProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export default function EventSearch({
  value,
  onChange,
  placeholder = "Search events...",
}: EventSearchProps) {
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
      <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
        <span className="text-lg text-gray-500">🔍</span>
      </div>
      <input
        type="text"
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-gray-700 bg-gray-800 py-3 pl-10 pr-4 text-white placeholder-gray-500 transition-all focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-600"
      />
      {localValue && (
        <button
          onClick={() => {
            setLocalValue("");
            onChange("");
          }}
          className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-500 transition-colors hover:text-gray-300"
          aria-label="Clear search"
        >
          ✕
        </button>
      )}
    </div>
  );
}
