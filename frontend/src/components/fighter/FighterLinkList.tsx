"use client";

import { Fragment } from "react";

import { cn } from "@/lib/utils";

import { FighterLink, type FighterLinkVariant } from "./FighterLink";

export interface FighterLinkListItem {
  fighterId?: string | null;
  name: string | null | undefined;
}

export interface FighterLinkListProps {
  fighters: FighterLinkListItem[];
  variant?: FighterLinkVariant;
  separator?: string;
  className?: string;
}

/**
 * Render comma-separated fighter references with consistent styling and
 * accessible fallbacks when IDs are missing.
 */
export function FighterLinkList({
  fighters,
  variant = "inline",
  separator = ", ",
  className,
}: FighterLinkListProps) {
  const filtered = fighters.filter(
    (fighter) => typeof fighter.name === "string" && fighter.name.trim().length > 0,
  );

  if (!filtered.length) {
    return null;
  }

  return (
    <span className={cn("inline-flex flex-wrap items-center gap-1", className)}>
      {filtered.map((fighter, index) => (
        <Fragment key={`${fighter.fighterId ?? fighter.name}-${index}`}>
          {index > 0 ? <span className="text-muted-foreground">{separator}</span> : null}
          <FighterLink
            fighterId={fighter.fighterId ?? null}
            name={fighter.name ?? ""}
            variant={variant}
          />
        </Fragment>
      ))}
    </span>
  );
}
