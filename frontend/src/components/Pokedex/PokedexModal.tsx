"use client";

import { ReactNode } from "react";

type Props = {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
};

export default function PokedexModal({ open, onClose, children }: Props) {
  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur"
      role="dialog"
      aria-modal="true"
    >
      <div className="relative w-full max-w-2xl rounded-2xl border-4 border-pokedexBlue bg-slate-900 p-6 shadow-xl">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 rounded-full border border-slate-700 px-2 py-1 text-xs uppercase text-slate-300 hover:border-pokedexYellow hover:text-pokedexYellow"
          aria-label="Close"
        >
          Close
        </button>
        {children}
      </div>
    </div>
  );
}
