"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import type { FighterListItem } from "@/lib/types";

/**
 * EXAMPLE IMPLEMENTATION: Command Palette
 *
 * Modern command palette (Cmd+K) for quick navigation and actions.
 * Inspired by VS Code, Notion, and Linear.
 *
 * To use this:
 * 1. Install cmdk: npm install cmdk
 * 2. Add keyboard shortcut detection
 * 3. Integrate with your search API
 * 4. Add to your root layout
 *
 * Features:
 * - Fuzzy search across fighters
 * - Quick actions (navigate, favorite, compare)
 * - Recent searches
 * - Keyboard navigation
 * - Smart suggestions
 */

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

type ActionType =
  | "navigate"
  | "favorite"
  | "compare"
  | "search"
  | "page"
  | "recent";

interface CommandAction {
  id: string;
  type: ActionType;
  label: string;
  subtitle?: string;
  icon?: React.ReactNode;
  onSelect: () => void;
  keywords?: string[];
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [fighters, setFighters] = useState<FighterListItem[]>([]);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Keyboard shortcut handler
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onClose();
      }
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [onClose]);

  // Load recent searches from localStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      const recent = localStorage.getItem("ufc-recent-searches");
      if (recent) {
        setRecentSearches(JSON.parse(recent));
      }
    }
  }, []);

  // Save search to recents
  const saveSearch = useCallback((query: string) => {
    if (!query.trim()) return;

    setRecentSearches((prev) => {
      const updated = [query, ...prev.filter((s) => s !== query)].slice(0, 5);
      if (typeof window !== "undefined") {
        localStorage.setItem("ufc-recent-searches", JSON.stringify(updated));
      }
      return updated;
    });
  }, []);

  // Debounced search
  useEffect(() => {
    if (!search) {
      setFighters([]);
      return;
    }

    setIsLoading(true);
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(
          `/api/search?q=${encodeURIComponent(search)}&limit=8`
        );
        const data = await response.json();
        setFighters(data.fighters || []);
      } catch (error) {
        console.error("Search error:", error);
      } finally {
        setIsLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [search]);

  // Navigate to fighter
  const navigateToFighter = useCallback(
    (fighterId: string, name: string) => {
      saveSearch(name);
      router.push(`/fighters/${fighterId}`);
      onClose();
    },
    [router, onClose, saveSearch]
  );

  // Navigate to page
  const navigateToPage = useCallback(
    (path: string, label: string) => {
      saveSearch(label);
      router.push(path);
      onClose();
    },
    [router, onClose, saveSearch]
  );

  // Quick actions
  const quickActions: CommandAction[] = [
    {
      id: "home",
      type: "page",
      label: "Go to Home",
      subtitle: "Browse all fighters",
      icon: (
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
          />
        </svg>
      ),
      onSelect: () => navigateToPage("/", "Home"),
      keywords: ["home", "fighters", "browse"],
    },
    {
      id: "stats",
      type: "page",
      label: "Go to Stats Hub",
      subtitle: "View analytics and leaderboards",
      icon: (
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          />
        </svg>
      ),
      onSelect: () => navigateToPage("/stats", "Stats Hub"),
      keywords: ["stats", "analytics", "leaderboards", "rankings"],
    },
    {
      id: "fightweb",
      type: "page",
      label: "Go to FightWeb",
      subtitle: "Explore fighter connections",
      icon: (
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
          />
        </svg>
      ),
      onSelect: () => navigateToPage("/fightweb", "FightWeb"),
      keywords: ["fightweb", "network", "graph", "connections"],
    },
    {
      id: "favorites",
      type: "page",
      label: "Go to Favorites",
      subtitle: "View your saved fighters",
      icon: (
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
          />
        </svg>
      ),
      onSelect: () => navigateToPage("/favorites", "Favorites"),
      keywords: ["favorites", "saved", "collection"],
    },
  ];

  // Filter quick actions based on search
  const filteredActions = quickActions.filter((action) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      action.label.toLowerCase().includes(searchLower) ||
      action.subtitle?.toLowerCase().includes(searchLower) ||
      action.keywords?.some((k) => k.includes(searchLower))
    );
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm">
      <div className="flex min-h-screen items-start justify-center p-4 pt-[10vh]">
        <Command
          className="w-full max-w-2xl overflow-hidden rounded-2xl border border-border/80 bg-background shadow-2xl"
          shouldFilter={false}
        >
          {/* Search Input */}
          <div className="flex items-center border-b border-border/80 px-4">
            <svg
              className="mr-3 h-5 w-5 text-muted-foreground"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <Command.Input
              placeholder="Search fighters, stats, or navigate..."
              className="w-full bg-transparent py-4 text-foreground outline-none placeholder:text-muted-foreground"
              value={search}
              onValueChange={setSearch}
              autoFocus
            />
            {isLoading && (
              <div className="ml-3 h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
            )}
          </div>

          <Command.List className="max-h-[60vh] overflow-y-auto p-2">
            <Command.Empty className="py-12 text-center text-sm text-muted-foreground">
              No results found
            </Command.Empty>

            {/* Recent Searches */}
            {!search && recentSearches.length > 0 && (
              <Command.Group
                heading="Recent Searches"
                className="mb-2 px-2 py-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground"
              >
                {recentSearches.map((recent, index) => (
                  <Command.Item
                    key={`recent-${index}`}
                    value={recent}
                    onSelect={() => setSearch(recent)}
                    className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-muted"
                  >
                    <svg
                      className="h-4 w-4 text-muted-foreground"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    <span>{recent}</span>
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {/* Quick Actions */}
            {(!search || filteredActions.length > 0) && (
              <Command.Group
                heading="Quick Actions"
                className="mb-2 px-2 py-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground"
              >
                {filteredActions.map((action) => (
                  <Command.Item
                    key={action.id}
                    value={action.label}
                    onSelect={action.onSelect}
                    className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-muted"
                  >
                    {action.icon && (
                      <div className="flex h-8 w-8 items-center justify-center rounded-md bg-muted text-muted-foreground">
                        {action.icon}
                      </div>
                    )}
                    <div className="flex-1">
                      <div className="text-sm font-medium text-foreground">
                        {action.label}
                      </div>
                      {action.subtitle && (
                        <div className="text-xs text-muted-foreground">
                          {action.subtitle}
                        </div>
                      )}
                    </div>
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {/* Fighter Results */}
            {fighters.length > 0 && (
              <Command.Group
                heading="Fighters"
                className="mb-2 px-2 py-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground"
              >
                {fighters.map((fighter) => (
                  <Command.Item
                    key={fighter.fighter_id}
                    value={fighter.name}
                    onSelect={() =>
                      navigateToFighter(fighter.fighter_id, fighter.name)
                    }
                    className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-muted"
                  >
                    {/* Fighter Avatar */}
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-gray-700 to-gray-800 text-xs font-bold text-white">
                      {fighter.name
                        .split(" ")
                        .map((n) => n[0])
                        .join("")
                        .toUpperCase()
                        .slice(0, 2)}
                    </div>

                    {/* Fighter Info */}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-foreground">
                          {fighter.name}
                        </span>
                        {fighter.nickname && (
                          <span className="text-xs text-muted-foreground">
                            &quot;{fighter.nickname}&quot;
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{fighter.division}</span>
                        <span>•</span>
                        <span>{fighter.record}</span>
                        {fighter.stance && (
                          <>
                            <span>•</span>
                            <span>{fighter.stance}</span>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Navigate Icon */}
                    <svg
                      className="h-4 w-4 text-muted-foreground"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  </Command.Item>
                ))}
              </Command.Group>
            )}
          </Command.List>

          {/* Footer with Keyboard Hints */}
          <div className="flex items-center justify-between border-t border-border/80 px-4 py-3 text-xs text-muted-foreground">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1">
                <kbd className="rounded bg-muted px-1.5 py-0.5 font-mono">↑↓</kbd>
                <span>Navigate</span>
              </div>
              <div className="flex items-center gap-1">
                <kbd className="rounded bg-muted px-1.5 py-0.5 font-mono">↵</kbd>
                <span>Select</span>
              </div>
              <div className="flex items-center gap-1">
                <kbd className="rounded bg-muted px-1.5 py-0.5 font-mono">esc</kbd>
                <span>Close</span>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <span>Powered by</span>
              <span className="font-semibold">UFC Pokedex</span>
            </div>
          </div>
        </Command>
      </div>
    </div>
  );
}

/**
 * Hook to control command palette
 *
 * Usage in root layout:
 *
 * ```tsx
 * "use client";
 *
 * import { useState, useEffect } from "react";
 * import { CommandPalette } from "@/components/search/CommandPalette";
 *
 * export function CommandPaletteProvider({ children }: { children: React.ReactNode }) {
 *   const [isOpen, setIsOpen] = useState(false);
 *
 *   useEffect(() => {
 *     const down = (e: KeyboardEvent) => {
 *       if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
 *         e.preventDefault();
 *         setIsOpen(true);
 *       }
 *     };
 *
 *     document.addEventListener("keydown", down);
 *     return () => document.removeEventListener("keydown", down);
 *   }, []);
 *
 *   return (
 *     <>
 *       {children}
 *       <CommandPalette isOpen={isOpen} onClose={() => setIsOpen(false)} />
 *     </>
 *   );
 * }
 * ```
 */
