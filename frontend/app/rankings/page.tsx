import type { Metadata } from "next";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import client from "@/lib/api-client";

export const metadata: Metadata = {
  title: "Rankings • UFC Fighter Pokedex",
  description: "View current UFC fighter rankings across all weight classes from FightMatrix.",
};

// Force dynamic rendering to get fresh rankings data
export const dynamic = 'force-dynamic';

export default async function RankingsPage() {
  // Fetch all current rankings from FightMatrix
  const { data, error } = await client.GET("/rankings/", {
    params: {
      query: { source: "fightmatrix" }
    }
  });

  if (error || !data) {
    return (
      <section className="container flex flex-col gap-12 py-12">
        <header className="space-y-4">
          <Badge variant="outline" className="w-fit tracking-[0.35em]">
            Rankings
          </Badge>
          <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
            Fighter Rankings
          </h1>
        </header>
        <div
          className="rounded-3xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive-foreground"
          role="alert"
        >
          Failed to load rankings data. Please try again later.
        </div>
      </section>
    );
  }

  const { divisions, division_rank_dates, total_fighters } = data;

  return (
    <section className="container flex flex-col gap-12 py-12">
      <header className="space-y-4">
        <Badge variant="outline" className="w-fit tracking-[0.35em]">
          Rankings
        </Badge>
        <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
          Fighter Rankings
        </h1>
        <p className="max-w-2xl text-lg text-muted-foreground">
          Current UFC fighter rankings across all weight classes from FightMatrix historical data.
        </p>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>Total Fighters: {total_fighters}</span>
          <span>•</span>
          <span>Source: FightMatrix</span>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        {divisions.map((division) => {
          const dateInfo = division_rank_dates.find(d => d.division === division.division);

          return (
            <Card key={division.division}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>{division.division}</span>
                  {division.total_fighters > 0 && (
                    <Badge variant="outline" className="text-xs">
                      {division.total_fighters} fighters
                    </Badge>
                  )}
                </CardTitle>
                {dateInfo && (
                  <CardDescription>
                    Updated: {new Date(dateInfo.rank_date).toLocaleDateString()}
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent>
                {division.rankings.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No rankings available for this division.
                  </p>
                ) : (
                  <ol className="space-y-2">
                    {division.rankings.slice(0, 5).map((entry) => (
                      <li
                        key={entry.ranking_id}
                        className="flex items-center justify-between text-sm"
                      >
                        <Link
                          href={`/fighters/${entry.fighter_id}`}
                          className="flex items-center gap-3 hover:underline"
                        >
                          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs font-semibold">
                            {entry.rank === 0 ? "C" : entry.rank ?? "NR"}
                          </span>
                          <span className="font-medium">{entry.fighter_name}</span>
                          {entry.nickname && (
                            <span className="text-muted-foreground">
                              &ldquo;{entry.nickname}&rdquo;
                            </span>
                          )}
                        </Link>
                        {entry.rank_movement !== 0 && (
                          <Badge
                            variant={entry.rank_movement > 0 ? "default" : "destructive"}
                            className="text-xs"
                          >
                            {entry.rank_movement > 0 ? "↑" : "↓"}
                            {Math.abs(entry.rank_movement)}
                          </Badge>
                        )}
                      </li>
                    ))}
                  </ol>
                )}
                {division.rankings.length > 5 && (
                  <Link
                    href={`/rankings/${encodeURIComponent(division.division)}`}
                    className="mt-4 block text-sm font-medium text-primary hover:underline"
                  >
                    View all {division.total_fighters} fighters →
                  </Link>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
