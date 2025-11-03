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
      <Input
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Search fighters by name or nickname..."
        aria-label="Search fighters"
        className="flex-1 bg-background/70"
      />
      <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
        <Button type="submit" className="w-full sm:w-auto">
          Search
        </Button>
        {value ? (
          <Button
            type="button"
            variant="ghost"
            className="w-full sm:w-auto"
            onClick={() => {
              setValue("");
              setSearchTerm("");
            }}
          >
            Reset
          </Button>
        ) : null}
      </div>
    </form>
  );
}
