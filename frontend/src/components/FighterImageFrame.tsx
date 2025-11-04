"use client";

import type { PropsWithChildren } from "react";

import { cn } from "@/lib/utils";

type FighterImageFrameProps = PropsWithChildren<{
  /**
   * Controls the base width of the rendered frame so the component can be reused in
   * both compact card layouts and the roomier fighter detail page. The sizing maps to
   * Tailwind width utilities while keeping the animated treatment identical.
   */
  size?: "md" | "lg";
  /**
   * Optional className hook for one-off adjustments when embedding the frame in a
   * layout with bespoke spacing requirements.
   */
  className?: string;
}>;

/**
 * Animated gradient wrapper used for fighter portraits throughout the application.
 * The component centralises the decorative border so both the list and detail
 * experiences share the same visual language. Hover states are handled via a named
 * Tailwind group so that children (the actual image element or placeholder) can react
 * with subtle scale and lighting transitions.
 */
export default function FighterImageFrame({
  size = "md",
  className,
  children,
}: FighterImageFrameProps) {
  const widthClass = size === "lg" ? "w-48 max-w-[240px]" : "w-40";

  return (
    <div
      className={cn(
        "group/fighter-frame relative isolate flex aspect-[3/4] items-center justify-center overflow-visible rounded-[1.45rem] p-[3px]",
        "bg-gradient-to-br from-rose-500/70 via-amber-400/55 to-emerald-400/70 bg-[length:260%_260%] animate-border-glow",
        "shadow-subtle transition-all duration-700 ease-out hover:shadow-[0_24px_66px_-30px_rgba(15,23,42,0.78)]",
        widthClass,
        className
      )}
    >
      <div
        className={cn(
          "relative flex h-full w-full items-center justify-center overflow-hidden rounded-[1.18rem] bg-background/95",
          "backdrop-blur-sm ring-1 ring-white/10 transition duration-700 ease-out",
          "group-hover/fighter-frame:bg-background/80 group-hover/fighter-frame:ring-white/20"
        )}
      >
        {children}
        <div className="pointer-events-none absolute inset-0 rounded-[1.18rem] bg-gradient-to-br from-white/10 via-transparent to-white/5 opacity-0 transition-opacity duration-700 group-hover/fighter-frame:opacity-100" />
      </div>
      <div className="pointer-events-none absolute inset-[-25%] -z-10 rounded-[2.25rem] bg-[radial-gradient(circle_at_top,_rgba(244,114,182,0.2),_rgba(14,165,233,0)_55%)] opacity-0 transition-opacity duration-700 group-hover/fighter-frame:opacity-80" />
    </div>
  );
}
