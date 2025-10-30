"use client";

import { useState } from "react";

import { useFavoritesStore } from "@/store/favoritesStore";

export default function SearchBar() {
  const setSearchTerm = useFavoritesStore((state) => state.setSearchTerm);
  const [value, setValue] = useState("");

  return (
    <form
      className="flex flex-col gap-2 md:flex-row"
      onSubmit={(event) => {
        event.preventDefault();
        setSearchTerm(value);
      }}
    >
      <input
        value={value}
        onChange={(event) => setValue(event.target.value)}
        className="flex-1 rounded-lg border border-slate-800 bg-slate-900 px-4 py-2 text-sm text-slate-100 outline-none focus:border-pokedexYellow"
        placeholder="Search fighters by name or nickname..."
      />
      <button
        type="submit"
        className="rounded-lg bg-pokedexYellow px-4 py-2 text-sm font-semibold text-slate-900 transition hover:bg-pokedexYellow/80"
      >
        Search
      </button>
    </form>
  );
}
