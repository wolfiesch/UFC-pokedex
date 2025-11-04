"use client";

import { useState } from "react";

import { useFavoritesStore } from "@/store/favoritesStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function SearchBar() {
  const setSearchTerm = useFavoritesStore((state) => state.setSearchTerm);
  const [value, setValue] = useState("");

  return (
    <form
      className="flex flex-col gap-3 rounded-3xl border border-border bg-card/70 p-4 shadow-subtle sm:flex-row sm:items-center"
      onSubmit={(event) => {
        event.preventDefault();
        setSearchTerm(value.trim());
      }}
    >
      <div className="relative flex-1">
        <Input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Search fighters by name or nickname..."
          aria-label="Search fighters"
          className="bg-background/70 pr-10"
        />
        {value && (
          <button
            type="button"
            onClick={() => {
              setValue("");
              setSearchTerm("");
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
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
        )}
      </div>
      <Button type="submit" className="w-full sm:w-auto">
        Search
      </Button>
    </form>
  );
}
