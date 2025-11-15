"use client";

import Link from "next/link";
import { cloneElement, isValidElement } from "react";
import type { ReactElement, ReactNode } from "react";

import { useFighterLookup } from "@/hooks/useFighterLookup";
import { getFighterProfileHref } from "@/lib/fighter-utils";
import { cn } from "@/lib/utils";

export type FighterLinkVariant = "inline" | "pill";

export interface FighterLinkProps {
  fighterId?: string | null;
  name: string;
  variant?: FighterLinkVariant;
  asChild?: boolean;
  prefetch?: boolean;
  className?: string;
  children?: ReactNode;
}

const VARIANT_STYLES: Record<FighterLinkVariant, string> = {
  inline:
    "text-primary underline-offset-4 hover:underline focus-visible:ring-0 focus-visible:underline",
  pill: "rounded-full border border-primary/40 bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-primary hover:border-primary/60 hover:bg-primary/20",
};

function resolveContent(children: ReactNode, fallback: string): ReactNode {
  if (children === null || typeof children === "undefined") {
    return fallback;
  }
  return children;
}

/**
 * Canonical linking primitive for fighter profile surfaces. Automatically
 * converts fighter IDs into the correct href and transparently falls back to
 * plain text when the ID is unavailable.
 */
export function FighterLink({
  fighterId,
  name,
  variant = "inline",
  asChild = false,
  prefetch,
  className,
  children,
}: FighterLinkProps) {
  const lookupTarget = fighterId ? null : name;
  const lookup = useFighterLookup(lookupTarget, { enabled: !fighterId });
  const resolvedId = fighterId ?? lookup.fighterId;
  const href = resolvedId ? getFighterProfileHref(resolvedId) : null;

  const content = resolveContent(children, name);
  const classes = cn(
    "inline-flex items-center gap-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background transition",
    VARIANT_STYLES[variant],
    className,
  );
  const ariaLabel = `View fighter profile for ${name}`;

  if (!href) {
    return (
      <span className={classes} aria-live={lookup.isLoading ? "polite" : "off"}>
        {content}
      </span>
    );
  }

  if (asChild && isValidElement(content)) {
    const element = content as ReactElement;
    const mergedClassName = cn(classes, element.props.className);
    return cloneElement(element, {
      className: mergedClassName,
      href,
      "aria-label": ariaLabel,
    });
  }

  return (
    <Link href={href} prefetch={prefetch} className={classes} aria-label={ariaLabel}>
      {content}
    </Link>
  );
}
