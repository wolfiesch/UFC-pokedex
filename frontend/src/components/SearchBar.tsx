"use client";

import { useEffect, useRef, useState } from "react";

import { useFavoritesStore } from "@/store/favoritesStore";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type SearchBarProps = {
  isLoading?: boolean;
};

export default function SearchBar({ isLoading = false }: SearchBarProps) {
  const current = useFavoritesStore((state) => state.searchTerm);
  const setSearchTerm = useFavoritesStore((state) => state.setSearchTerm);
  const [value, setValue] = useState(current ?? "");
  const isUpdatingRef = useRef(false);
  const prevStoreRef = useRef(current);

  // Sync only when the store actually changes (external changes)
  useEffect(() => {
    if (current !== prevStoreRef.current) {
      prevStoreRef.current = current;
      setValue(current ?? "");
    }
  }, [current]);

  // Debounce: push to store 400ms after typing stops
  useEffect(() => {
    const trimmed = value.trim();
    const trimmedStore = (current ?? "").trim();
    if (trimmed === trimmedStore) return;

    const t = window.setTimeout(() => {
      isUpdatingRef.current = true;
      setSearchTerm(trimmed);
    }, 400);
    return () => window.clearTimeout(t);
  }, [value, current, setSearchTerm]);

  const handleClear = () => {
    setValue("");
    isUpdatingRef.current = true;
    setSearchTerm("");
  };

  return (
    <div className="flex flex-col gap-3 rounded-3xl border border-border bg-card/70 p-4 shadow-subtle sm:flex-row sm:items-center">
      <div className="relative flex-1">
        {/* Left search icon */}
        <svg
          className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>

        <Input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Search fighters by name or nickname..."
          aria-label="Search fighters"
          className={cn(
            "bg-background/70 pl-10",
            value ? "pr-20" : "pr-12"
          )}
        />

        {/* Right controls */}
        <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-2">
          {isLoading ? (
            <svg
              className="h-4 w-4 animate-spin text-muted-foreground"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              aria-label="Searching..."
            >
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          ) : null}

          {value ? (
            <button
              type="button"
              onClick={handleClear}
              className="rounded-full p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              aria-label="Clear search"
            >
              <svg
                className="h-4 w-4"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
