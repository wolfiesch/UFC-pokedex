"use client";

import { useState, useEffect } from "react";
import { CommandPalette } from "../search/CommandPalette";

export function CommandPaletteProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  return (
    <>
      {children}
      <CommandPalette isOpen={open} onClose={() => setOpen(false)} />
    </>
  );
}
