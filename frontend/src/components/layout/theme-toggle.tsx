"use client";

import { Moon, Sun } from "lucide-react";
import { ButtonHTMLAttributes, DetailedHTMLProps, memo } from "react";

import { useTheme } from "@/components/providers/ThemeProvider";
import { cn } from "@/lib/utils";

/**
 * Props accepted by the theme toggle button. Keeping the definition explicit
 * allows additional DOM attributes (e.g. `aria-*` labels) to be forwarded
 * cleanly while maintaining strong typing. The `className` property is kept
 * optional so that callers can blend their own layout styles with the defaults.
 */
export type ThemeToggleProps = DetailedHTMLProps<
  ButtonHTMLAttributes<HTMLButtonElement>,
  HTMLButtonElement
>;

/**
 * Icon button that flips between light and dark mode using the ThemeProvider
 * context. A memoized component avoids unnecessary re-renders whenever parent
 * components update for unrelated reasons.
 */
function ThemeToggleBase({ className, ...props }: ThemeToggleProps): JSX.Element {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      aria-label="Toggle color theme"
      className={cn(
        "relative inline-flex h-10 w-10 items-center justify-center rounded-full border border-border/80 bg-muted/60 text-foreground transition-colors hover:bg-muted",
        className,
      )}
      onClick={toggleTheme}
      {...props}
    >
      <Sun
        className={cn(
          "absolute h-5 w-5 transition-opacity",
          theme === "light" ? "opacity-100" : "opacity-0",
        )}
        aria-hidden={theme !== "light"}
      />
      <Moon
        className={cn(
          "absolute h-5 w-5 transition-opacity",
          theme === "dark" ? "opacity-100" : "opacity-0",
        )}
        aria-hidden={theme !== "dark"}
      />
      <span className="sr-only">Switch between dark and light themes</span>
    </button>
  );
}

export const ThemeToggle = memo(ThemeToggleBase);

ThemeToggle.displayName = "ThemeToggle";
