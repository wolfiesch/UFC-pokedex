"use client";

import { useState } from "react";
import Link from "next/link";

import StatsDisplay from "@/components/StatsDisplay";
import type { FighterDetail } from "@/lib/types";
import type { ApiError } from "@/lib/errors";
import { ErrorType } from "@/lib/errors";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import FighterImagePlaceholder from "@/components/FighterImagePlaceholder";
import FighterImageFrame from "@/components/FighterImageFrame";
import { resolveImageUrl } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { StatsRadarChart } from "@/components/visualizations/StatsRadarChart";
import { RecordBreakdownChart } from "@/components/visualizations/RecordBreakdownChart";
import { PerformanceBarCharts } from "@/components/visualizations/PerformanceBarCharts";
import { FightHistoryTimeline } from "@/components/visualizations/FightHistoryTimeline";

type Props = {
  fighterId: string;
  fighter: FighterDetail | null;
  isLoading: boolean;
  error?: ApiError | null;
  onRetry?: () => void;
};

export default function FighterDetailCard({ fighterId, fighter, isLoading, error, onRetry }: Props) {
  // Hooks must be called at the top level, before any conditional returns
  const [imageError, setImageError] = useState(false);
  const fightHistory =
    fighter?.fight_history?.filter((fight) => fight.event_name !== null) ?? [];
  const imageSrc = resolveImageUrl(
    fighter?.resolved_image_url ?? fighter?.image_url ?? undefined,
  );
  const shouldShowImage = Boolean(imageSrc) && !imageError;

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
                  <span className="font-semibold">Error Type:</span> {error.errorType}
                </p>
                <p>
                  <span className="font-semibold">Status Code:</span> {error.statusCode}
                </p>
                {error.requestId && (
                  <p>
                    <span className="font-semibold">Request ID:</span> {error.requestId}
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
                  className="h-full w-full scale-[1.01] object-contain drop-shadow-[0_22px_35px_rgba(15,23,42,0.45)] transition duration-700 ease-out group-hover/fighter-frame:scale-[1.06] group-hover/fighter-frame:rotate-[0.65deg]"
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
            <div className="flex items-center gap-3 flex-wrap">
              <CardTitle className="text-3xl">{fighter.name}</CardTitle>
              {fighter.is_current_champion && (
                <Badge className="bg-gradient-to-r from-yellow-500 to-amber-600 text-white font-bold border-0">
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
                <Badge variant="outline" className="font-semibold border-amber-600/50 text-amber-600 dark:text-amber-500">
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
            {fighter.nickname ? (
              <CardDescription className="text-base tracking-tight text-muted-foreground">
                &ldquo;{fighter.nickname}&rdquo;
              </CardDescription>
            ) : null}
            <p className="text-sm text-muted-foreground">
              {fighter.record ?? "Record unavailable"}
            </p>
            <div className="flex flex-wrap gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">
              <Badge variant="outline">{fighter.division ?? "Unknown Division"}</Badge>
              {fighter.stance ? <Badge variant="outline">{fighter.stance}</Badge> : null}
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
          <StatsDisplay title="Significant Strikes" stats={fighter.significant_strikes} />
        ) : null}
        {Object.keys(fighter.takedown_stats).length > 0 ? (
          <StatsDisplay title="Takedowns" stats={fighter.takedown_stats} />
        ) : null}
        {Object.keys(fighter.career).length > 0 ? (
          <StatsDisplay title="Career" stats={fighter.career} />
        ) : null}

        {/* Fight History Timeline */}
        {fightHistory.length > 0 ? (
          <FightHistoryTimeline
            fightHistory={fightHistory}
            fighterName={fighter.name}
          />
        ) : null}

        {fightHistory.length > 0 ? (
          <section className="space-y-4">
            <h3 className="text-xl font-semibold">Fight History (Table View)</h3>

            {/* Desktop table view */}
            <div className="hidden md:block overflow-x-auto">
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
                      <TableCell className="font-medium">{fight.event_name}</TableCell>
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
                      <TableCell className="text-center">{fight.round ?? "—"}</TableCell>
                      <TableCell className="text-center">{fight.time ?? "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Mobile card view */}
            <div className="md:hidden space-y-3">
              {fightHistory.map((fight) => (
                <Card key={fight.fight_id} className="p-4">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <h4 className="font-semibold text-sm">{fight.event_name}</h4>
                        <p className="text-xs text-muted-foreground mt-0.5">
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
                        <p className="text-xs text-muted-foreground">Opponent</p>
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
      </CardContent>
    </Card>
  );
}

function Info({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="rounded-2xl border border-border/70 bg-background/60 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 text-base">{value ?? "—"}</p>
    </div>
  );
}
