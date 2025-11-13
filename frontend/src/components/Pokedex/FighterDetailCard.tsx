/* eslint-disable @next/next/no-img-element */
"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { toast } from "sonner";

import StatsDisplay from "@/components/StatsDisplay";
import type { FighterDetail } from "@/lib/types";
import type { ApiError } from "@/lib/errors";
import { ErrorType } from "@/lib/errors";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import FighterImagePlaceholder from "@/components/FighterImagePlaceholder";
import FighterImageFrame from "@/components/FighterImageFrame";
import { resolveImageUrl, cn } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useFavorites } from "@/hooks/useFavorites";
import RankingHistoryChart from "@/components/rankings/RankingHistoryChart";
import PeakRanking from "@/components/rankings/PeakRanking";
import client from "@/lib/api-client";

const ChartSkeleton = ({ title }: { title: string }) => (
  <Card className="bg-card/60">
    <CardHeader>
      <CardTitle className="text-base text-muted-foreground">{title}</CardTitle>
    </CardHeader>
    <CardContent className="h-64 animate-pulse rounded-2xl bg-muted/40" />
  </Card>
);

const StatsRadarChart = dynamic(
  () =>
    import("@/components/visualizations/StatsRadarChart").then((mod) => ({
      default: mod.StatsRadarChart,
    })),
  { ssr: false, loading: () => <ChartSkeleton title="Performance Overview" /> },
);

const RecordBreakdownChart = dynamic(
  () =>
    import("@/components/visualizations/RecordBreakdownChart").then((mod) => ({
      default: mod.RecordBreakdownChart,
    })),
  {
    ssr: false,
    loading: () => <ChartSkeleton title="Fight Record Breakdown" />,
  },
);

const PerformanceBarCharts = dynamic(
  () =>
    import("@/components/visualizations/PerformanceBarCharts").then((mod) => ({
      default: mod.PerformanceBarCharts,
    })),
  { ssr: false, loading: () => <ChartSkeleton title="Accuracy & Defense" /> },
);

const FightScatterDemo = dynamic(
  () =>
    import("@/components/analytics/FightScatterDemo").then((mod) => ({
      default: mod.FightScatterDemo,
    })),
  {
    ssr: false,
    loading: () => <ChartSkeleton title="Fight History Timeline" />,
  },
);

type Props = {
  fighterId: string;
  fighter: FighterDetail | null;
  isLoading: boolean;
  error?: ApiError | null;
  onRetry?: () => void;
};

export default function FighterDetailCard({
  fighterId,
  fighter,
  isLoading,
  error,
  onRetry,
}: Props) {
  // Hooks must be called at the top level, before any conditional returns
  const [imageError, setImageError] = useState(false);
  const { toggleFavorite, isFavorite } = useFavorites({
    autoInitialize: true,
  });
  const isFavorited = fighter ? isFavorite(fighter.fighter_id) : false;

  const [rankingHistory, setRankingHistory] = useState<any>(null);
  const [peakRanking, setPeakRanking] = useState<any>(null);
  const [rankingsLoading, setRankingsLoading] = useState(true);

  const fightHistory =
    fighter?.fight_history?.filter((fight) => fight.event_name !== null) ?? [];
  const imageSrc = resolveImageUrl(fighter?.image_url);
  const shouldShowImage = Boolean(imageSrc) && !imageError;

  // Fetch ranking data
  useEffect(() => {
    async function fetchRankings() {
      if (!fighter?.fighter_id) {
        setRankingsLoading(false);
        return;
      }

      try {
        setRankingsLoading(true);

        // Fetch history and peak in parallel
        const [historyRes, peakRes] = await Promise.all([
          client.GET("/rankings/fighter/{fighter_id}/history", {
            params: {
              path: { fighter_id: fighter.fighter_id },
              query: { source: "fightmatrix", limit: 50 },
            },
          }),
          client.GET("/rankings/fighter/{fighter_id}/peak", {
            params: {
              path: { fighter_id: fighter.fighter_id },
              query: { source: "fightmatrix" },
            },
          }),
        ]);

        // Only set data if the response was successful and contains actual data
        if (
          !historyRes.error &&
          historyRes.data &&
          historyRes.data.history &&
          historyRes.data.history.length > 0
        ) {
          setRankingHistory(historyRes.data);
        }

        if (
          !peakRes.error &&
          peakRes.data &&
          peakRes.data.peak_rank !== undefined
        ) {
          setPeakRanking(peakRes.data);
        }
      } catch (error) {
        // Silently handle errors - rankings data is optional
        // Most fighters won't have FightMatrix rankings
      } finally {
        setRankingsLoading(false);
      }
    }

    fetchRankings();
  }, [fighter?.fighter_id]);

  const handleFavoriteClick = () => {
    if (!fighter) return;

    const wasAdding = !isFavorited;
    toggleFavorite({
      fighter_id: fighter.fighter_id,
      detail_url: fighter.detail_url,
      name: fighter.name,
      nickname: fighter.nickname,
      division: fighter.division,
      record: fighter.record,
      height: fighter.height,
      weight: fighter.weight,
      reach: fighter.reach,
      leg_reach: fighter.leg_reach,
      stance: fighter.stance,
      dob: fighter.dob,
      image_url: fighter.image_url,
      is_current_champion: fighter.is_current_champion,
      is_former_champion: fighter.is_former_champion,
      was_interim: fighter.was_interim,
    });

    // Show toast notification
    if (wasAdding) {
      toast.success(`Added ${fighter.name} to favorites`);
    } else {
      toast(`Removed ${fighter.name} from favorites`);
    }
  };

  if (isLoading) {
    return (
      <Card className="rounded-3xl border-border bg-card/80 p-6 text-sm text-muted-foreground">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground/40 border-t-foreground" />
          Loading fighter details…
        </div>
      </Card>
    );
  }

  if (error) {
    const isNotFound = error.errorType === ErrorType.NOT_FOUND;

    return (
      <Card className="rounded-3xl border-destructive/30 bg-destructive/10 p-6">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0">
            <svg
              className="h-6 w-6 text-destructive"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              {isNotFound ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              )}
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="mb-1 font-semibold text-destructive-foreground">
              {isNotFound ? "Fighter not found" : "Unable to load fighter"}
            </h3>
            <p className="mb-2 text-sm text-destructive-foreground/90">
              {error.getUserMessage()}
            </p>

            {/* Technical details */}
            <details className="mb-4 text-xs text-destructive-foreground/75">
              <summary className="cursor-pointer hover:text-destructive-foreground">
                Technical Details
              </summary>
              <div className="mt-2 space-y-1 rounded-lg border border-destructive/20 bg-background/50 p-3 font-mono">
                <p>
                  <span className="font-semibold">Fighter ID:</span> {fighterId}
                </p>
                <p>
                  <span className="font-semibold">Error Type:</span>{" "}
                  {error.errorType}
                </p>
                <p>
                  <span className="font-semibold">Status Code:</span>{" "}
                  {error.statusCode}
                </p>
                {error.requestId && (
                  <p>
                    <span className="font-semibold">Request ID:</span>{" "}
                    {error.requestId}
                  </p>
                )}
                {error.timestamp && (
                  <p>
                    <span className="font-semibold">Timestamp:</span>{" "}
                    {error.timestamp.toLocaleString()}
                  </p>
                )}
              </div>
            </details>

            <div className="flex gap-2">
              {onRetry && !isNotFound && (
                <button
                  onClick={onRetry}
                  className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition-colors hover:bg-destructive/90"
                >
                  Retry
                </button>
              )}
              <a
                href="/"
                className="rounded-full border border-input bg-background px-4 py-2 text-sm font-semibold transition-colors hover:bg-accent hover:text-accent-foreground"
              >
                Go Back Home
              </a>
            </div>
          </div>
        </div>
      </Card>
    );
  }

  if (!fighter) {
    // Fallback if no error but also no fighter (shouldn't happen with new error handling)
    return (
      <Card className="rounded-3xl border-destructive/30 bg-destructive/10 p-6 text-sm text-destructive-foreground">
        Fighter with id <code>{fighterId}</code> was not found.
      </Card>
    );
  }

  /**
   * Keeps the fallback placeholder aligned with the shared FighterImageFrame interior
   * radius and layout so initials feel intentional within the glowing border.
   */
  const placeholderClass =
    "flex h-full w-full items-center justify-center rounded-[1.18rem] text-white";

  return (
    <Card className="space-y-8 rounded-3xl border-border bg-card/80">
      <CardHeader className="space-y-6 pb-0">
        <div className="grid gap-6 md:grid-cols-[220px_1fr] md:items-start">
          <div className="flex items-start justify-center">
            <FighterImageFrame size="lg" className="md:w-full">
              {shouldShowImage ? (
                <img
                  src={imageSrc ?? ""}
                  alt={fighter.name}
                  className="h-full w-full scale-[1.01] object-contain drop-shadow-[0_22px_35px_rgba(15,23,42,0.45)] transition duration-700 ease-out group-hover/fighter-frame:rotate-[0.65deg] group-hover/fighter-frame:scale-[1.06]"
                  loading="lazy"
                  onError={() => setImageError(true)}
                />
              ) : (
                <FighterImagePlaceholder
                  name={fighter.name}
                  division={fighter.division}
                  className={placeholderClass}
                />
              )}
            </FighterImageFrame>
          </div>
          <div className="flex flex-col gap-3">
            <div className="flex items-start justify-between gap-4">
              <div className="flex flex-wrap items-center gap-3">
                <CardTitle className="text-3xl">{fighter.name}</CardTitle>
                {fighter.is_current_champion && (
                  <Badge className="border-0 bg-gradient-to-r from-yellow-500 to-amber-600 font-bold text-white">
                    <svg
                      className="mr-1 h-4 w-4"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                    CURRENT CHAMPION
                  </Badge>
                )}
                {!fighter.is_current_champion && fighter.is_former_champion && (
                  <Badge
                    variant="outline"
                    className="border-amber-600/50 font-semibold text-amber-600 dark:text-amber-500"
                  >
                    <svg
                      className="mr-1 h-4 w-4"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                    FORMER CHAMPION
                  </Badge>
                )}
              </div>
              <Button
                variant={isFavorited ? "default" : "outline"}
                size="lg"
                onClick={handleFavoriteClick}
                className={cn(
                  "group/fav flex-shrink-0 transition-all",
                  isFavorited && "hover:scale-105",
                )}
              >
                <svg
                  className={cn(
                    "mr-2 h-5 w-5 transition-transform",
                    isFavorited
                      ? "fill-current group-hover/fav:scale-110"
                      : "fill-none group-hover/fav:scale-110",
                  )}
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"
                  />
                </svg>
                {isFavorited ? "Favorited" : "Add to Favorites"}
              </Button>
            </div>
            {fighter.nickname ? (
              <CardDescription className="text-base tracking-tight text-muted-foreground">
                &ldquo;{fighter.nickname}&rdquo;
              </CardDescription>
            ) : null}
            <p className="text-sm text-muted-foreground">
              {fighter.record ?? "Record unavailable"}
            </p>
            <div className="flex flex-wrap gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">
              <Badge variant="outline">
                {fighter.division ?? "Unknown Division"}
              </Badge>
              {fighter.stance ? (
                <Badge variant="outline">{fighter.stance}</Badge>
              ) : null}
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-8">
        <section>
          <dl className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
            <Info label="Height" value={fighter.height} />
            <Info label="Weight" value={fighter.weight} />
            <Info label="Reach" value={fighter.reach} />
            <Info label="Leg Reach" value={fighter.leg_reach} />
            <Info label="Stance" value={fighter.stance} />
            <Info label="DOB" value={fighter.dob ?? "—"} />
          </dl>
        </section>

        {/* Performance Visualizations */}
        <RecordBreakdownChart
          record={fighter.record}
          fightHistory={fightHistory}
        />

        <div className="grid gap-8 lg:grid-cols-2">
          <StatsRadarChart
            striking={fighter.striking}
            grappling={fighter.grappling}
          />
          <PerformanceBarCharts
            striking={fighter.striking}
            grappling={fighter.grappling}
          />
        </div>

        {/* Detailed Stats (collapsible sections) */}
        {Object.keys(fighter.striking).length > 0 ? (
          <StatsDisplay title="Striking" stats={fighter.striking} />
        ) : null}
        {Object.keys(fighter.grappling).length > 0 ? (
          <StatsDisplay title="Grappling" stats={fighter.grappling} />
        ) : null}
        {Object.keys(fighter.significant_strikes).length > 0 ? (
          <StatsDisplay
            title="Significant Strikes"
            stats={fighter.significant_strikes}
          />
        ) : null}
        {Object.keys(fighter.takedown_stats).length > 0 ? (
          <StatsDisplay title="Takedowns" stats={fighter.takedown_stats} />
        ) : null}
        {Object.keys(fighter.career).length > 0 ? (
          <StatsDisplay title="Career" stats={fighter.career} />
        ) : null}

        {/* Fight History Visualization */}
        {fightHistory.length > 0 ? (
          <section className="space-y-4">
            <h3 className="text-xl font-semibold">Fight History Analysis</h3>
            <FightScatterDemo fightHistory={fightHistory} />
          </section>
        ) : null}

        {fightHistory.length > 0 ? (
          <section className="space-y-4">
            <h3 className="text-xl font-semibold">
              Fight History (Table View)
            </h3>

            {/* Desktop table view */}
            <div className="hidden overflow-x-auto md:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Event</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Opponent</TableHead>
                    <TableHead className="text-center">Result</TableHead>
                    <TableHead>Method</TableHead>
                    <TableHead className="text-center">Round</TableHead>
                    <TableHead className="text-center">Time</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {fightHistory.map((fight) => (
                    <TableRow key={fight.fight_id}>
                      <TableCell className="font-medium">
                        {fight.event_name}
                      </TableCell>
                      <TableCell>{fight.event_date ?? "—"}</TableCell>
                      <TableCell>
                        {fight.opponent_id ? (
                          <Link
                            href={`/fighters/${fight.opponent_id}`}
                            className="text-primary underline-offset-4 hover:underline"
                          >
                            {fight.opponent}
                          </Link>
                        ) : (
                          fight.opponent
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge
                          variant={
                            fight.result.toLowerCase().includes("win")
                              ? "default"
                              : "outline"
                          }
                        >
                          {fight.result}
                        </Badge>
                      </TableCell>
                      <TableCell>{fight.method}</TableCell>
                      <TableCell className="text-center">
                        {fight.round ?? "—"}
                      </TableCell>
                      <TableCell className="text-center">
                        {fight.time ?? "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Mobile card view */}
            <div className="space-y-3 md:hidden">
              {fightHistory.map((fight) => (
                <Card key={fight.fight_id} className="p-4">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <h4 className="text-sm font-semibold">
                          {fight.event_name}
                        </h4>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {fight.event_date ?? "—"}
                        </p>
                      </div>
                      <Badge
                        variant={
                          fight.result.toLowerCase().includes("win")
                            ? "default"
                            : "outline"
                        }
                      >
                        {fight.result}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <p className="text-xs text-muted-foreground">
                          Opponent
                        </p>
                        <p className="font-medium">
                          {fight.opponent_id ? (
                            <Link
                              href={`/fighters/${fight.opponent_id}`}
                              className="text-primary underline-offset-4 hover:underline"
                            >
                              {fight.opponent}
                            </Link>
                          ) : (
                            fight.opponent
                          )}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Method</p>
                        <p>{fight.method}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Round</p>
                        <p>{fight.round ?? "—"}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Time</p>
                        <p>{fight.time ?? "—"}</p>
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </section>
        ) : null}

        {/* Rankings Section */}
        {!rankingsLoading && (rankingHistory || peakRanking) && (
          <section className="space-y-6">
            <h3 className="text-xl font-semibold">Rankings</h3>
            <div className="grid gap-6 lg:grid-cols-2">
              {peakRanking && (
                <PeakRanking
                  fighterName={fighter.name}
                  division={peakRanking.division}
                  peakRank={peakRanking.peak_rank}
                  rankDate={peakRanking.rank_date}
                  isInterim={peakRanking.is_interim}
                  source={peakRanking.source}
                />
              )}
              {rankingHistory && rankingHistory.history.length > 0 && (
                <div className="lg:col-span-2">
                  <RankingHistoryChart
                    fighterName={fighter.name}
                    history={rankingHistory.history}
                  />
                </div>
              )}
            </div>
          </section>
        )}
      </CardContent>
    </Card>
  );
}

function Info({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  return (
    <div className="rounded-2xl border border-border/70 bg-background/60 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 text-base">{value ?? "—"}</p>
    </div>
  );
}
