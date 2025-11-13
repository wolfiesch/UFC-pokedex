import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "outline";

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-foreground text-background",
  outline: "border border-border text-foreground",
};

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export function Badge({
  className,
  variant = "default",
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-tight",
        variantStyles[variant],
        className,
      )}
      {...props}
    />
  );
}
