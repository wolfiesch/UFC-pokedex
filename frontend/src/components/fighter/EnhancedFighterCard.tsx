"use client";

import { memo, useState, useRef, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  motion,
  AnimatePresence,
  useMotionValue,
  useSpring,
  useTransform,
} from "framer-motion";
import type { FighterListItem } from "@/lib/types";
import { useFighterDetails } from "@/hooks/useFighterDetails";
import { RankFlagBadge } from "@/components/rankings/RankFlagBadge";
import { useFavorites } from "@/hooks/useFavorites";
import { useComparison } from "@/hooks/useComparison";
import { resolveImageUrl, getInitials } from "@/lib/utils";
import CountryFlag from "@/components/CountryFlag";
import {
  calculateStreak,
  getLastFight,
  formatFightDate,
  getRelativeTime,
  formatShortDate,
} from "@/lib/fighter-utils";
import { toCountryIsoCode } from "@/lib/countryCodes";

interface EnhancedFighterCardProps {
  fighter: FighterListItem;
  priority?: boolean; // For LCP optimization - set to true for first card
}

/**
 * Fight status badge component for displaying upcoming/recent fights
 */
interface FightBadgeProps {
  fighter: FighterListItem;
}

function FightBadge({ fighter }: FightBadgeProps): JSX.Element | null {
  const today = new Date();
  const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

  // Priority 1: Upcoming fight
  if (fighter.next_fight_date) {
    const nextDate = new Date(fighter.next_fight_date);
    if (nextDate > today) {
      return (
        <span className="flex items-center gap-1 text-muted-foreground">
          <span>⚔️</span>
          <span>{formatShortDate(nextDate)}</span>
        </span>
      );
    }
  }

  // Priority 2: Recent fight (last 30 days)
  if (fighter.last_fight_date && fighter.last_fight_result) {
    const lastDate = new Date(fighter.last_fight_date);
    if (lastDate >= thirtyDaysAgo && lastDate <= today) {
      const isWin = fighter.last_fight_result === "win";
      const isLoss = fighter.last_fight_result === "loss";

      if (isWin || isLoss) {
        return (
          <span className="flex items-center gap-1 text-muted-foreground">
            <span className={isWin ? "text-green-500" : "text-red-500"}>
              {isWin ? "🟢" : "🔴"}
            </span>
            <span>{getRelativeTime(fighter.last_fight_date)}</span>
          </span>
        );
      }
    }
  }

  return null;
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
function EnhancedFighterCardComponent({
  fighter,
  priority = false,
}: EnhancedFighterCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [detailsEnabled, setDetailsEnabled] = useState(false);
  const [imageError, setImageError] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  // 3D Parallax Motion Values
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  // Spring animation for smooth movement
  const springConfig = { stiffness: 150, damping: 20 };
  const rotateX = useSpring(
    useTransform(mouseY, [-0.5, 0.5], [10, -10]),
    springConfig,
  );
  const rotateY = useSpring(
    useTransform(mouseX, [-0.5, 0.5], [-10, 10]),
    springConfig,
  );

  // Hooks
  const { isFavorite, toggleFavorite } = useFavorites({
    autoInitialize: false,
  });
  const { addToComparison, isInComparison } = useComparison();
  const {
    details,
    isLoading: isLoadingDetails,
    error: detailsError,
  } = useFighterDetails(fighter.fighter_id, detailsEnabled);

  useEffect(() => {
    const cardNode = cardRef.current;
    if (!cardNode || detailsEnabled) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setDetailsEnabled(true);
            observer.disconnect();
          }
        });
      },
      {
        rootMargin: "200px 0px",
        threshold: 0.35,
      },
    );

    observer.observe(cardNode);

    return () => {
      observer.disconnect();
    };
  }, [detailsEnabled, fighter.fighter_id]);

  // Mouse move handler for 3D parallax effect
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;

    const rect = cardRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    // Calculate normalized position (-0.5 to 0.5)
    const x = (e.clientX - centerX) / (rect.width / 2);
    const y = (e.clientY - centerY) / (rect.height / 2);

    mouseX.set(x);
    mouseY.set(y);
  };

  // Reset position when mouse leaves
  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

  // Trigger quick stats overlay + ensure details fetch
  const handleHoverStart = () => {
    setIsHovered(true);
    setDetailsEnabled(true);
  };

  const handleHoverEnd = () => {
    setIsHovered(false);
    handleMouseLeave();
  };

  // Computed values
  const isFavorited = isFavorite(fighter.fighter_id);
  const isInComparisonList = isInComparison(fighter.fighter_id);
  const imageSrc = resolveImageUrl(fighter.image_url);
  const shouldShowImage = Boolean(imageSrc) && !imageError;
  const nationalityFlag = toCountryIsoCode(fighter.nationality ?? undefined);

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
  // Only use detailed streak when actively fetching/hovering, otherwise use lightweight streak
  const detailedStreak =
    details && detailsEnabled ? calculateStreak(details.fight_history) : null;
  const streak = detailedStreak || listStreak;
  const lastFight =
    details && detailsEnabled ? getLastFight(details.fight_history) : null;

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
      ref={cardRef}
      className="group relative h-full"
      onHoverStart={handleHoverStart}
      onHoverEnd={handleHoverEnd}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        perspective: "1000px",
        transformStyle: "preserve-3d",
      }}
    >
      <Link
        href={`/fighters/${fighter.fighter_id}`}
        className="flex h-full flex-col"
      >
        <motion.div
          className={`relative flex h-full flex-col overflow-hidden rounded-2xl border border-border/80 bg-card/80 backdrop-blur-sm transition-colors transition-shadow duration-300 hover:border-border hover:shadow-lg hover:shadow-black/5 ${championGlowClass}`}
          style={{
            rotateX,
            rotateY,
            transformStyle: "preserve-3d",
          }}
        >
          {/* Quick Actions Toolbar */}
          <AnimatePresence>
            {isHovered && (
              <motion.div
                className="absolute right-3 top-3 z-20 flex gap-2"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                style={{
                  transform: "translateZ(40px)",
                  transformStyle: "preserve-3d",
                }}
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
          <div
            className="relative aspect-[3/4] flex-shrink-0 overflow-hidden bg-gradient-to-br from-gray-800 to-gray-900"
            style={{
              transform: "translateZ(-20px)",
              transformStyle: "preserve-3d",
            }}
          >
            {/* Depth Layer 1: Deep background glow (moves most) */}
            <div
              className="absolute inset-0 bg-gradient-radial from-primary/30 via-primary/10 to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100"
              style={{
                transform: "translateZ(-40px) scale(1.2)",
                transformStyle: "preserve-3d",
                filter: "blur(40px)",
              }}
            />

            {/* Depth Layer 2: Mid-ground glow */}
            <div
              className="absolute inset-0 bg-gradient-radial from-primary/20 via-primary/5 to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100"
              style={{
                transform: "translateZ(-25px) scale(1.1)",
                transformStyle: "preserve-3d",
                filter: "blur(20px)",
              }}
            />

            {/* Fighter Image (foreground) */}
            {shouldShowImage ? (
              <div
                className="relative h-full w-full"
                style={{
                  transform: "translateZ(5px)",
                  transformStyle: "preserve-3d",
                }}
              >
                <Image
                  src={imageSrc!}
                  alt={fighter.name}
                  fill
                  className="object-cover transition-transform duration-500 group-hover:scale-110"
                  sizes="(max-width: 768px) 50vw, (max-width: 1200px) 33vw, 25vw"
                  priority={priority}
                  onError={() => setImageError(true)}
                />

                {/* Rim light effect - subtle edge glow on hover */}
                <div
                  className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100"
                  style={{
                    background:
                      "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.15) 0%, transparent 50%)",
                    mixBlendMode: "overlay",
                  }}
                />
              </div>
            ) : (
              <div
                className={`flex h-full items-center justify-center bg-gradient-to-br ${getDivisionColor(
                  fighter.division,
                )}`}
              >
                <span className="text-6xl font-bold text-white/20">
                  {getInitials(fighter.name)}
                </span>
              </div>
            )}

            {/* Champion Badges - Stay at top left */}
            <div
              className="absolute left-3 top-3 flex flex-col gap-2"
              style={{
                transform: "translateZ(30px)",
                transformStyle: "preserve-3d",
              }}
            >
              {fighter.is_current_champion && (
                <span className="flex items-center gap-1 rounded-full bg-gradient-to-r from-yellow-500 to-amber-600 px-3 py-1 text-xs font-bold text-white backdrop-blur-sm">
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
                <span className="flex items-center gap-1 rounded-full border border-amber-600/70 bg-black/60 px-3 py-1 text-xs font-semibold text-amber-500 backdrop-blur-sm">
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

            {/* Bottom Left Stack: Empty now - streak moved to compact row */}
            <div
              className="absolute bottom-3 left-3 flex flex-col items-start gap-1.5"
              style={{
                transform: "translateZ(25px)",
                transformStyle: "preserve-3d",
              }}
            >
              {/* Streak Badge moved to compact stats row */}
            </div>

            {/* Bottom Right Stack: RankFlagBadge only */}
            <div
              className="absolute bottom-3 right-3 flex flex-col items-end gap-1.5"
              style={{
                transform: "translateZ(25px)",
                transformStyle: "preserve-3d",
              }}
            >
              {/* RankFlagBadge */}
              <RankFlagBadge
                currentRank={fighter.current_rank}
                peakRank={fighter.peak_rank}
                isChampion={fighter.is_current_champion}
                isInterimChampion={fighter.was_interim}
              />
            </div>

            {/* Quick Stats Overlay on Hover */}
            <AnimatePresence>
              {isHovered && (
                <motion.div
                  className="absolute inset-0 bg-black/85 backdrop-blur-sm overflow-hidden"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="flex h-full flex-col text-white">
                    {detailsError ? (
                      <div className="flex flex-1 flex-col items-center justify-center gap-2 px-6 text-center">
                        <div className="rounded-full bg-white/10 p-3">
                          <svg
                            className="h-6 w-6 text-white/70"
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
                        </div>
                        <span className="text-sm text-white/70">
                          Failed to load stats
                        </span>
                        <span className="text-xs text-white/50">
                          Click for full profile
                        </span>
                      </div>
                    ) : (
                      <>
                        <div className="px-6 pb-3 pt-6 text-center">
                          <h4 className="text-sm font-semibold uppercase tracking-wider text-white/60">
                            Quick Stats
                          </h4>

                          {isLoadingDetails && !details && (
                            <div className="mt-2 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs text-white/70">
                              <div className="h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                              <span>Fetching fight details...</span>
                            </div>
                          )}
                        </div>

                        <div className="flex-1 space-y-4 overflow-y-auto px-6 pb-6">
                          {/* Last Fight / Next Fight Info */}
                          <div className="w-full min-h-[116px] rounded-2xl bg-white/10 p-4 shadow-inner">
                            {lastFight ? (
                              (() => {
                                const isUpcoming =
                                  lastFight.result?.toLowerCase() === "next" ||
                                  (lastFight.date &&
                                    new Date(lastFight.date) > new Date());
                                return (
                                  <div className="flex h-full flex-col justify-between gap-2">
                                    <div className="space-y-1">
                                      <div className="mb-1 text-xs text-white/60">
                                        {isUpcoming
                                          ? "Next Fight"
                                          : "Last Fight"}
                                      </div>
                                      <div className="text-sm font-bold">
                                        {lastFight.result} vs{" "}
                                        {lastFight.opponent}
                                      </div>
                                      {lastFight.method ? (
                                        <div className="text-xs text-white/70">
                                          {lastFight.method}
                                        </div>
                                      ) : null}
                                    </div>
                                    <div className="text-xs text-white/50">
                                      {getRelativeTime(lastFight.date)}
                                    </div>
                                  </div>
                                );
                              })()
                            ) : detailsEnabled ? (
                              <div className="space-y-2">
                                {isLoadingDetails ? (
                                  <>
                                    <div className="h-3 w-24 animate-pulse rounded-full bg-white/20" />
                                    <div className="h-4 w-3/4 animate-pulse rounded-full bg-white/30" />
                                    <div className="h-3 w-1/2 animate-pulse rounded-full bg-white/20" />
                                  </>
                                ) : (
                                  <p className="text-center text-xs text-white/60">
                                    Fight history data is on the way.
                                  </p>
                                )}
                              </div>
                            ) : (
                              <div className="text-center text-xs text-white/60">
                                Hover to load recent fight data.
                              </div>
                            )}
                          </div>

                          <div className="grid w-full grid-cols-2 gap-3">
                            <div className="rounded-xl bg-white/10 p-3 text-center">
                              <div className="text-2xl font-bold leading-tight">
                                {fighter.record}
                              </div>
                              <div className="text-xs text-white/60">Record</div>
                            </div>

                            {streak && streak.count >= 2 && (
                              <div className="rounded-xl bg-white/10 p-3 text-center">
                                <div className="text-lg font-bold leading-tight">
                                  {streak.label}
                                </div>
                                <div className="text-xs text-white/60">
                                  Current Streak
                                </div>
                              </div>
                            )}

                            {fighter.stance && (
                              <div className="rounded-xl bg-white/10 p-3 text-center">
                                <div className="text-lg font-bold leading-tight">
                                  {fighter.stance}
                                </div>
                                <div className="text-xs text-white/60">
                                  Stance
                                </div>
                              </div>
                            )}

                            {fighter.height && (
                              <div className="rounded-xl bg-white/10 p-3 text-center">
                                <div className="text-lg font-bold leading-tight">
                                  {fighter.height}
                                </div>
                                <div className="text-xs text-white/60">
                                  Height
                                </div>
                              </div>
                            )}

                            {fighter.reach && (
                              <div className="rounded-xl bg-white/10 p-3 text-center">
                                <div className="text-lg font-bold leading-tight">
                                  {fighter.reach}
                                </div>
                                <div className="text-xs text-white/60">
                                  Reach
                                </div>
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center justify-center gap-2 px-6 pb-6 pt-3 text-xs text-white/80">
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
          <div
            className="flex flex-1 flex-col p-4"
            style={{
              transform: "translateZ(10px)",
              transformStyle: "preserve-3d",
            }}
          >
            <div className="mb-2 min-h-[3rem]">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-bold text-foreground transition-colors group-hover:text-primary">
                  {fighter.name}
                </h3>
                {fighter.is_current_champion && (
                  <span
                    className="text-lg text-amber-500"
                    title="Current Champion"
                  >
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

            {/* Compact Stats Row with All Badges */}
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <div className="flex flex-wrap items-center gap-2">
                {/* Record */}
                <span className="font-medium">{fighter.record}</span>

                {/* Division */}
                {fighter.division && (
                  <>
                    <span>•</span>
                    <span>{fighter.division}</span>
                  </>
                )}

                {/* Win Streak Badge */}
                {streak && streak.count >= 2 && (
                  <>
                    <span>•</span>
                    <span
                      className={`flex items-center gap-0.5 ${
                        streak.type === "win"
                          ? "text-green-500"
                          : streak.type === "loss"
                            ? "text-red-500"
                            : "text-gray-500"
                      }`}
                    >
                      {streak.type === "win"
                        ? "🟢"
                        : streak.type === "loss"
                          ? "🔴"
                          : "⚫"}
                      <span className="font-medium">{streak.label}</span>
                    </span>
                  </>
                )}

                {/* Fight Status Badge */}
                <FightBadge fighter={fighter} />
              </div>

              <div className="flex items-center gap-2">
                {nationalityFlag && (
                  <div className="flex items-center gap-1">
                    <CountryFlag
                      countryCode={nationalityFlag}
                      width={16}
                      height={12}
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Fighting Out Of Section */}
            {fighter.fighting_out_of && (
              <div className="mt-3 border-t border-border/50 pt-3">
                <div className="mb-1 text-xs text-muted-foreground">
                  Fighting Out Of
                </div>
                <div className="flex items-center gap-2 text-sm text-foreground">
                  {nationalityFlag && (
                    <CountryFlag
                      countryCode={nationalityFlag}
                      width={20}
                      height={14}
                    />
                  )}
                  {fighter.fighting_out_of}
                </div>
              </div>
            )}
          </div>

          {/* View Profile Footer */}
          <div
            className="flex-shrink-0 border-t border-border/50 bg-muted/30 px-4 py-2"
            style={{
              transform: "translateZ(15px)",
              transformStyle: "preserve-3d",
            }}
          >
            <div className="flex items-center justify-center text-xs">
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
        </motion.div>
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
  nextProps: Readonly<EnhancedFighterCardProps>,
): boolean => {
  const previousFighter = previousProps.fighter;
  const nextFighter = nextProps.fighter;

  // Ensure shallow equality across the curated key set so the card only
  // re-renders when user-facing details actually change.
  return fighterEqualityKeys.every(
    (key) => previousFighter[key] === nextFighter[key],
  );
};

export const EnhancedFighterCard = memo(
  EnhancedFighterCardComponent,
  areFighterCardPropsEqual,
);
