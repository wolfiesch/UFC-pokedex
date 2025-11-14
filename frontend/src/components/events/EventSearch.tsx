"use client";

import { useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { Search, X } from "lucide-react";

interface EventSearchProps {
  /**
   * The externally controlled search string.
   */
  value: string;
  /**
   * Handler invoked after the debounce window whenever the search term changes.
   */
  onChange: (value: string) => void;
  /**
   * Placeholder copy to render inside the input field.
   */
  placeholder?: string;
  /**
   * Optional wrapper class name for layout composition.
   */
  className?: string;
  /**
   * Optional override for the input element styling so the search can blend into glassmorphic toolbars.
   */
  inputClassName?: string;
  /**
   * Custom debounce duration in milliseconds.
   */
  debounceMs?: number;
}

export default function EventSearch({
  value,
  onChange,
  placeholder = "Search UFC events, venues, or fighters",
  className,
  inputClassName,
  debounceMs = 250,
}: EventSearchProps) {
  const [localValue, setLocalValue] = useState(value);

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  useEffect(() => {
    const timer = setTimeout(() => {
      onChange(localValue.trimStart());
    }, debounceMs);

    return () => clearTimeout(timer);
  }, [localValue, onChange, debounceMs]);

  const hasQuery = useMemo(() => localValue.length > 0, [localValue]);

  return (
    <div
      className={clsx(
        "relative flex items-center rounded-2xl border border-white/10 bg-white/10 px-4 shadow-inner backdrop-blur transition focus-within:border-white/20 focus-within:bg-white/20",
        className,
      )}
    >
      <Search className="mr-3 h-5 w-5 text-white/60" />
      <input
        type="text"
        value={localValue}
        onChange={(event) => setLocalValue(event.target.value)}
        placeholder={placeholder}
        className={clsx(
          "h-12 w-full bg-transparent text-sm text-white placeholder:text-white/40 focus:outline-none",
          inputClassName,
        )}
      />
      {hasQuery && (
        <button
          type="button"
          onClick={() => {
            setLocalValue("");
            onChange("");
          }}
          className="ml-3 inline-flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-white/70 transition hover:bg-white/20 hover:text-white"
          aria-label="Clear search"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
