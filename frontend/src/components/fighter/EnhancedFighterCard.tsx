"use client";

import { memo, useState, useRef, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import type { FighterListItem } from "@/lib/types";
import { useFighterDetails } from "@/hooks/useFighterDetails";
import { RankFlagBadge } from "@/components/rankings/RankFlagBadge";
import { useFavorites } from "@/hooks/useFavorites";
import { useComparison } from "@/hooks/useComparison";
import { resolveImageUrl, getInitials } from "@/lib/utils";
import {
  calculateStreak,
  getLastFight,
  formatFightDate,
  getRelativeTime,
} from "@/lib/fighter-utils";

interface EnhancedFighterCardProps {
  fighter: FighterListItem;
  priority?: boolean; // For LCP optimization - set to true for first card
}

/**
 * Enhanced Fighter Card with lazy loading and advanced features
 *
 * Features:
 * - Hover states with quick stats preview
 * - Lazy loading of fight history on hover
 * - Last fight info and win/loss streak
 * - Quick actions (favorite, comparison)
 * - Performance indicators
 * - Smooth animations
 * - Better visual hierarchy
 */
function EnhancedFighterCardComponent({ fighter, priority = false }: EnhancedFighterCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [imageError, setImageError] = useState(false);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Hooks
  const { isFavorite, toggleFavorite } = useFavorites({ autoInitialize: false });
  const { addToComparison, isInComparison } = useComparison();
  const { details, isLoading: isLoadingDetails, error: detailsError } = useFighterDetails(
    fighter.fighter_id,
    isHovered
  );

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
      }
    };
  }, []);

  // Debounced hover handlers (300ms delay to prevent unnecessary API calls)
  const handleHoverStart = () => {
    hoverTimeoutRef.current = setTimeout(() => {
      setIsHovered(true);
    }, 300);
  };

  const handleHoverEnd = () => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    setIsHovered(false);
  };

  // Computed values
  const isFavorited = isFavorite(fighter.fighter_id);
  const isInComparisonList = isInComparison(fighter.fighter_id);
  const imageSrc = resolveImageUrl(fighter.image_url);
  const shouldShowImage = Boolean(imageSrc) && !imageError;

  // Record pill uses fighter.record directly (no win% computation)

  // Calculate streak and last fight. Prefer server-provided lightweight streak
  // from the list payload, and upgrade to precise streak when details are
  // fetched (on hover).
  const listStreak = (() => {
    const count = fighter.current_streak_count ?? 0;
    const type = fighter.current_streak_type ?? "none";
    const isTyped = type === "win" || type === "loss" || type === "draw";
    if (isTyped && count >= 2) {
      return { type, count, label: String(count) } as const;
    }
    return null;
  })();
  const streak = details
    ? calculateStreak(details.fight_history)
    : listStreak;
  const lastFight = details ? getLastFight(details.fight_history) : null;

  // Division color coding
  const getDivisionColor = (division?: string | null) => {
    const colors: Record<string, string> = {
      Flyweight: "from-blue-500/20 to-blue-600/20",
      Bantamweight: "from-green-500/20 to-green-600/20",
      Featherweight: "from-yellow-500/20 to-yellow-600/20",
      Lightweight: "from-orange-500/20 to-orange-600/20",
      Welterweight: "from-red-500/20 to-red-600/20",
      Middleweight: "from-purple-500/20 to-purple-600/20",
      "Light Heavyweight": "from-pink-500/20 to-pink-600/20",
      Heavyweight: "from-gray-500/20 to-gray-600/20",
    };
    return colors[division || ""] || "from-gray-500/20 to-gray-600/20";
  };

  const championGlowClass = fighter.is_current_champion
    ? "ring-2 ring-yellow-500/60 shadow-[0_0_20px_rgba(234,179,8,0.3)]"
    : fighter.is_former_champion
    ? "ring-1 ring-amber-500/40 shadow-[0_0_12px_rgba(245,158,11,0.2)]"
    : "";

  return (
    <motion.div
      className="group relative h-full"
      onHoverStart={handleHoverStart}
      onHoverEnd={handleHoverEnd}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Link href={`/fighters/${fighter.fighter_id}`} className="h-full flex flex-col">
        <div className={`relative flex h-full flex-col overflow-hidden rounded-2xl border border-border/80 bg-card/80 backdrop-blur-sm transition-all duration-300 hover:border-border hover:shadow-lg hover:shadow-black/5 hover:-translate-y-1 ${championGlowClass}`}>
          {/* Quick Actions Toolbar */}
          <AnimatePresence>
            {isHovered && (
              <motion.div
                className="absolute top-3 right-3 z-20 flex gap-2"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
              >
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    toggleFavorite(fighter);
                  }}
                  className={`rounded-full p-2 backdrop-blur-md transition-colors ${
                    isFavorited
                      ? "bg-yellow-500/90 text-white"
                      : "bg-black/40 text-white/90 hover:bg-black/60"
                  }`}
                  aria-label="Toggle favorite"
                >
                  <svg
                    className="h-4 w-4"
                    fill={isFavorited ? "currentColor" : "none"}
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
                    />
                  </svg>
                </button>

                <button
                  onClick={(e) => {
                    e.preventDefault();
                    addToComparison(fighter.fighter_id, fighter.name);
                  }}
                  className={`rounded-full p-2 backdrop-blur-md transition-colors ${
                    isInComparisonList
                      ? "bg-blue-500/90 text-white"
                      : "bg-black/40 text-white/90 hover:bg-black/60"
                  }`}
                  aria-label="Add to comparison"
                >
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    />
                  </svg>
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Fighter Image/Avatar Section */}
          <div className="relative flex-shrink-0 aspect-[3/4] overflow-hidden bg-gradient-to-br from-gray-800 to-gray-900">
            {shouldShowImage ? (
              <Image
                src={imageSrc!}
                alt={fighter.name}
                fill
                className="object-cover transition-transform duration-500 group-hover:scale-110"
                sizes="(max-width: 768px) 50vw, (max-width: 1200px) 33vw, 25vw"
                priority={priority}
                onError={() => setImageError(true)}
              />
            ) : (
              <div
                className={`flex h-full items-center justify-center bg-gradient-to-br ${getDivisionColor(
                  fighter.division
                )}`}
              >
                <span className="text-6xl font-bold text-white/20">
                  {getInitials(fighter.name)}
                </span>
              </div>
            )}

            {/* Division, Ranking, and Champion Badges */}
            <div className="absolute top-3 left-3 flex flex-col gap-2">
              <RankFlagBadge
                currentRank={fighter.current_rank}
                peakRank={fighter.peak_rank}
                isChampion={fighter.is_current_champion}
                isInterimChampion={fighter.was_interim}
              />
              {fighter.is_current_champion && (
                <span className="rounded-full bg-gradient-to-r from-yellow-500 to-amber-600 px-3 py-1 text-xs font-bold text-white backdrop-blur-sm flex items-center gap-1">
                  <svg
                    className="h-3 w-3"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  {fighter.was_interim ? "CHAMP (I)" : "CHAMP"}
                </span>
              )}
              {!fighter.is_current_champion && fighter.is_former_champion && (
                <span className="rounded-full border border-amber-600/70 bg-black/60 px-3 py-1 text-xs font-semibold text-amber-500 backdrop-blur-sm flex items-center gap-1">
                  <svg
                    className="h-3 w-3"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  {fighter.was_interim ? "FORMER (I)" : "FORMER"}
                </span>
              )}
            </div>

            {fighter.division && (
              <div className="absolute top-3 right-3">
                <span className="rounded-full bg-black/60 px-3 py-1 text-xs font-semibold text-white backdrop-blur-sm">
                  {fighter.division}
                </span>
              </div>
            )}

            {/* Record Badge */}
            {fighter.record && (
              <div className="absolute bottom-3 left-3">
                <span className="rounded-full bg-gray-700/90 px-2 py-1 text-xs font-semibold text-gray-200 backdrop-blur-sm">
                  {fighter.record}
                </span>
              </div>
            )}

            {/* Streak Badge */}
            {streak && streak.count >= 2 && (
              <div className="absolute bottom-3 right-3 z-20">
                <div
                  className={`flex items-center gap-1 rounded-full px-2 py-1 backdrop-blur-sm ${
                    streak.type === "win"
                      ? "bg-green-500/90"
                      : streak.type === "loss"
                        ? "bg-red-500/90"
                        : "bg-gray-500/90"
                  }`}
                >
                  <span className="text-xs font-bold text-white">{streak.label}</span>
                </div>
              </div>
            )}

            {/* Quick Stats Overlay on Hover */}
            <AnimatePresence>
              {isHovered && (
                <motion.div
                  className="absolute inset-0 bg-black/85 backdrop-blur-sm"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="flex h-full flex-col items-center justify-center gap-4 p-6 text-white">
                    {isLoadingDetails ? (
                      <div className="flex items-center gap-2">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-white" />
                        <span className="text-sm text-white/60">Loading stats...</span>
                      </div>
                    ) : detailsError ? (
                      <div className="flex flex-col items-center gap-2 text-center">
                        <svg
                          className="h-8 w-8 text-white/40"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                        <span className="text-sm text-white/60">Failed to load stats</span>
                        <span className="text-xs text-white/40">Click for full profile</span>
                      </div>
                    ) : (
                      <>
                        <h4 className="text-center text-sm font-semibold uppercase tracking-wider text-white/60">
                          Quick Stats
                        </h4>

                        {/* Last Fight / Next Fight Info */}
                        {lastFight && (
                          <div className="w-full rounded-lg bg-white/10 p-3">
                            {(() => {
                              const isUpcoming =
                                lastFight.result?.toLowerCase() === "next" ||
                                (lastFight.date && new Date(lastFight.date) > new Date());
                              return (
                                <>
                                  <div className="mb-1 text-xs text-white/60">
                                    {isUpcoming ? "Next Fight" : "Last Fight"}
                                  </div>
                                  <div className="text-sm font-bold">
                                    {lastFight.result} vs {lastFight.opponent}
                                  </div>
                                  <div className="text-xs text-white/70">
                                    {lastFight.method}
                                  </div>
                                  <div className="mt-1 text-xs text-white/50">
                                    {getRelativeTime(lastFight.date)}
                                  </div>
                                </>
                              );
                            })()}
                          </div>
                        )}

                        <div className="grid w-full grid-cols-2 gap-3">
                          <div className="rounded-lg bg-white/10 p-3 text-center">
                            <div className="text-2xl font-bold">{fighter.record}</div>
                            <div className="text-xs text-white/60">Record</div>
                          </div>

                          {streak && streak.count >= 2 && (
                            <div className="rounded-lg bg-white/10 p-3 text-center">
                              <div className="text-lg font-bold">{streak.label}</div>
                              <div className="text-xs text-white/60">Current Streak</div>
                            </div>
                          )}

                          {fighter.stance && (
                            <div className="rounded-lg bg-white/10 p-3 text-center">
                              <div className="text-lg font-bold">{fighter.stance}</div>
                              <div className="text-xs text-white/60">Stance</div>
                            </div>
                          )}

                          {fighter.height && (
                            <div className="rounded-lg bg-white/10 p-3 text-center">
                              <div className="text-lg font-bold">{fighter.height}</div>
                              <div className="text-xs text-white/60">Height</div>
                            </div>
                          )}

                          {fighter.reach && (
                            <div className="rounded-lg bg-white/10 p-3 text-center">
                              <div className="text-lg font-bold">{fighter.reach}</div>
                              <div className="text-xs text-white/60">Reach</div>
                            </div>
                          )}
                        </div>

                        <div className="mt-2 flex items-center gap-2 text-xs text-white/80">
                          <svg
                            className="h-4 w-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M13 7l5 5m0 0l-5 5m5-5H6"
                            />
                          </svg>
                          <span>Click for full profile</span>
                        </div>
                      </>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Fighter Info Section */}
          <div className="flex flex-1 flex-col p-4">
            <div className="mb-2 min-h-[3rem]">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="font-bold text-foreground transition-colors group-hover:text-primary">
                  {fighter.name}
                </h3>
                {fighter.is_current_champion && (
                  <span className="text-amber-500 text-lg" title="Current Champion">
                    ⭐
                  </span>
                )}
              </div>
              {fighter.nickname ? (
                <p className="text-sm text-muted-foreground">
                  &quot;{fighter.nickname}&quot;
                </p>
              ) : (
                <div className="h-5" />
              )}
            </div>

            {/* Compact Stats Row */}
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{fighter.record}</span>
              {fighter.stance && <span>{fighter.stance}</span>}
            </div>
          </div>

          {/* View Profile Footer */}
          <div className="flex-shrink-0 border-t border-border/50 bg-muted/30 px-4 py-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">{fighter.division}</span>
              <span className="flex items-center gap-1 font-medium text-primary transition-all group-hover:gap-2">
                View Profile
                <svg
                  className="h-3 w-3"
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
              </span>
            </div>
          </div>
        </div>
      </Link>
    </motion.div>
  );
}

const fighterEqualityKeys: Array<keyof FighterListItem> = [
  "fighter_id",
  "name",
  "nickname",
  "record",
  "division",
  "image_url",
  "is_current_champion",
  "is_former_champion",
  "current_streak_type",
  "current_streak_count",
];

const areFighterCardPropsEqual = (
  previousProps: Readonly<EnhancedFighterCardProps>,
  nextProps: Readonly<EnhancedFighterCardProps>
): boolean => {
  const previousFighter = previousProps.fighter;
  const nextFighter = nextProps.fighter;

  // Ensure shallow equality across the curated key set so the card only
  // re-renders when user-facing details actually change.
  return fighterEqualityKeys.every(
    (key) => previousFighter[key] === nextFighter[key]
  );
};

export const EnhancedFighterCard = memo(
  EnhancedFighterCardComponent,
  areFighterCardPropsEqual
);
