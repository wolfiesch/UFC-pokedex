"use client";

import { ReactNode } from "react";

import { Button } from "@/components/ui/button";

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
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/70 backdrop-blur"
      role="dialog"
      aria-modal="true"
    >
      <div className="relative w-full max-w-3xl rounded-3xl border border-border bg-card p-8 shadow-2xl">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onClose}
          className="absolute right-4 top-4"
          aria-label="Close modal"
        >
          Close
        </Button>
        {children}
      </div>
    </div>
  );
}
