"use client";

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
import { resolveImageUrl } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type Props = {
  fighterId: string;
  fighter: FighterDetail | null;
  isLoading: boolean;
  error?: ApiError | null;
  onRetry?: () => void;
};

export default function FighterDetailCard({ fighterId, fighter, isLoading, error, onRetry }: Props) {
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

  const fightHistory = fighter.fight_history.filter((fight) => fight.event_name !== null);
  const imageSrc = resolveImageUrl(fighter.image_url);

  return (
    <Card className="space-y-8 rounded-3xl border-border bg-card/80">
      <CardHeader className="space-y-6 pb-0">
        <div className="grid gap-6 md:grid-cols-[220px_1fr] md:items-start">
          {imageSrc ? (
            <div className="flex items-start justify-center">
              <div className="relative aspect-[3/4] w-44 max-w-[220px] overflow-hidden rounded-2xl border border-border/70 bg-muted p-3 md:w-full">
                <img
                  src={imageSrc}
                  alt={fighter.name}
                  className="h-full w-full object-contain"
                  loading="lazy"
                  onError={(event) => {
                    (event.target as HTMLImageElement).style.display = "none";
                  }}
                />
              </div>
            </div>
          ) : null}
          <div className="flex flex-col gap-3">
            <CardTitle className="text-3xl">{fighter.name}</CardTitle>
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

        {fightHistory.length > 0 ? (
          <section className="space-y-4">
            <h3 className="text-xl font-semibold">Fight History</h3>
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
                    <TableCell>{fight.opponent}</TableCell>
                    <TableCell className="text-center">{fight.result}</TableCell>
                    <TableCell>{fight.method}</TableCell>
                    <TableCell className="text-center">{fight.round ?? "—"}</TableCell>
                    <TableCell className="text-center">{fight.time ?? "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
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
