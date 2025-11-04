"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import type { FighterListItem } from "@/lib/types";
import { useFighterDetails } from "@/hooks/useFighterDetails";
import { useFavorites } from "@/hooks/useFavorites";
import { useComparison } from "@/hooks/useComparison";
import { resolveImageUrl, getInitials } from "@/lib/utils";
import {
  parseRecord,
  calculateStreak,
  getLastFight,
  formatFightDate,
  getRelativeTime,
} from "@/lib/fighter-utils";

interface EnhancedFighterCardProps {
  fighter: FighterListItem;
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
export function EnhancedFighterCard({ fighter }: EnhancedFighterCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [imageError, setImageError] = useState(false);

  // Hooks
  const { favorites, toggleFavorite } = useFavorites();
  const { addToComparison, isInComparison } = useComparison();
  const { details, isLoading: isLoadingDetails } = useFighterDetails(
    fighter.fighter_id,
    isHovered
  );

  // Computed values
  const isFavorited = favorites.some((fav) => fav.fighter_id === fighter.fighter_id);
  const isInComparisonList = isInComparison(fighter.fighter_id);
  const imageSrc = resolveImageUrl(fighter.image_url);
  const shouldShowImage = Boolean(imageSrc) && !imageError;

  // Parse record for win percentage
  const parsedRecord = parseRecord(fighter.record);
  const winPercentage = parsedRecord?.winPercentage;

  // Calculate streak and last fight from details
  const streak = details ? calculateStreak(details.fight_history) : null;
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

  return (
    <motion.div
      className="group relative"
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Link href={`/fighters/${fighter.fighter_id}`}>
        <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-card/80 backdrop-blur-sm transition-all duration-300 hover:border-border hover:shadow-lg hover:shadow-black/5 hover:-translate-y-1">
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
          <div className="relative aspect-[3/4] overflow-hidden bg-gradient-to-br from-gray-800 to-gray-900">
            {shouldShowImage ? (
              <Image
                src={imageSrc!}
                alt={fighter.name}
                fill
                className="object-cover transition-transform duration-500 group-hover:scale-110"
                sizes="(max-width: 768px) 50vw, (max-width: 1200px) 33vw, 25vw"
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

            {/* Division Badge */}
            {fighter.division && (
              <div className="absolute top-3 left-3">
                <span className="rounded-full bg-black/60 px-3 py-1 text-xs font-semibold text-white backdrop-blur-sm">
                  {fighter.division}
                </span>
              </div>
            )}

            {/* Win Percentage Badge */}
            {winPercentage && (
              <div className="absolute bottom-3 left-3">
                <div className="flex items-center gap-1 rounded-full bg-green-500/90 px-2 py-1 backdrop-blur-sm">
                  <svg
                    className="h-3 w-3 text-white"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L11 10.586 14.586 7H12z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span className="text-xs font-bold text-white">{winPercentage}%</span>
                </div>
              </div>
            )}

            {/* Streak Badge */}
            {streak && streak.count > 0 && (
              <div className="absolute bottom-3 right-3">
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
                    ) : (
                      <>
                        <h4 className="text-center text-sm font-semibold uppercase tracking-wider text-white/60">
                          Quick Stats
                        </h4>

                        {/* Last Fight Info */}
                        {lastFight && (
                          <div className="w-full rounded-lg bg-white/10 p-3">
                            <div className="mb-1 text-xs text-white/60">Last Fight</div>
                            <div className="text-sm font-bold">
                              {lastFight.result} vs {lastFight.opponent}
                            </div>
                            <div className="text-xs text-white/70">
                              {lastFight.method}
                            </div>
                            <div className="mt-1 text-xs text-white/50">
                              {getRelativeTime(lastFight.date)}
                            </div>
                          </div>
                        )}

                        <div className="grid w-full grid-cols-2 gap-3">
                          <div className="rounded-lg bg-white/10 p-3 text-center">
                            <div className="text-2xl font-bold">{fighter.record}</div>
                            <div className="text-xs text-white/60">Record</div>
                          </div>

                          {streak && streak.count > 0 && (
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
          <div className="p-4">
            <div className="mb-2">
              <h3 className="font-bold text-foreground transition-colors group-hover:text-primary">
                {fighter.name}
              </h3>
              {fighter.nickname && (
                <p className="text-sm text-muted-foreground">
                  &quot;{fighter.nickname}&quot;
                </p>
              )}
            </div>

            {/* Compact Stats Row */}
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{fighter.record}</span>
              {fighter.stance && <span>{fighter.stance}</span>}
            </div>
          </div>

          {/* View Profile Footer */}
          <div className="border-t border-border/50 bg-muted/30 px-4 py-2">
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
