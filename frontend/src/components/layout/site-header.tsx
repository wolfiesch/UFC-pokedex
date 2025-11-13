"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/layout/theme-toggle";

const NAV_ITEMS = [
  { href: "/", label: "Home" },
  { href: "/explore", label: "Explore" },
  { href: "/events", label: "Events" },
  { href: "/stats", label: "Stats Hub" },
  { href: "/rankings", label: "Rankings" },
  { href: "/fightweb", label: "FightWeb" },
  { href: "/favorites", label: "Favorites" },
];

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border/80 bg-background/90 backdrop-blur">
      <div className="container flex h-16 items-center justify-between gap-6">
        <Link
          href="/"
          className="text-sm font-semibold uppercase tracking-[0.35em] text-foreground transition-colors hover:text-muted-foreground"
          aria-label="Return to the UFC Fighter Pokedex home page"
        >
          UFC POKEDEX
        </Link>
        <div className="flex items-center gap-3">
          <nav className="flex items-center gap-1 text-sm">
            {NAV_ITEMS.map((item) => {
              const isActive =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "rounded-full px-4 py-2 transition-colors",
                    isActive
                      ? "bg-foreground text-background"
                      : "text-foreground/80 hover:bg-muted",
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <ThemeToggle className="ml-1" />
        </div>
      </div>
    </header>
  );
}
