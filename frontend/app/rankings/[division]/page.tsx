import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import client from "@/lib/api-client";
import { getAllDivisionNamesSSR } from "@/lib/api-ssr";

type DivisionRankingsPageProps = {
  params: {
    division: string;
  };
};

export async function generateMetadata({
  params,
}: DivisionRankingsPageProps): Promise<Metadata> {
  const division = decodeURIComponent(params.division);

  return {
    title: `${division} Rankings • UFC Fighter Pokedex`,
    description: `View complete ${division} fighter rankings from FightMatrix.`,
  };
}

// Enable static export with revalidation
export const revalidate = 3600; // Revalidate every hour
export const dynamicParams = true;

/**
 * Generate static params for all divisions
 */
export async function generateStaticParams() {
  try {
    const divisions = await getAllDivisionNamesSSR();
    // For static export, ensure we have at least one param
    return divisions.length > 0 ? divisions : [{ division: "Lightweight" }];
  } catch (error) {
    console.error("Failed to generate static params for divisions:", error);
    // For static export, return a fallback division to avoid build error
    return [{ division: "Lightweight" }];
  }
}

export default async function DivisionRankingsPage({
  params,
}: DivisionRankingsPageProps) {
  const division = decodeURIComponent(params.division);

  let data = null;
  let error = null;

  // Wrap in try-catch to prevent any exceptions from failing the build
  try {
    const result = await client.GET("/rankings/{division}", {
      params: {
        path: { division },
        query: { source: "fightmatrix" }
      }
    });
    data = result.data;
    error = result.error;
  } catch (e) {
    console.warn(`Failed to fetch rankings for ${division}:`, e);
    error = e;
  }

  // For static export: render error UI instead of notFound()
  if (error || !data) {
    return (
      <section className="container flex flex-col gap-8 py-12">
        <header className="space-y-4">
          <Link
            href="/rankings"
            className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
          >
            ← Back to all rankings
          </Link>
          <Badge variant="outline" className="w-fit tracking-[0.35em]">
            Rankings
          </Badge>
          <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
            {division}
          </h1>
        </header>
        <div
          className="rounded-3xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive-foreground"
          role="alert"
        >
          Rankings data for {division} is not currently available. This division may not have been updated yet.
        </div>
      </section>
    );
  }

  const { rankings, rank_date, total_fighters } = data;

  // Separate champion from ranked fighters
  const champion = (rankings ?? []).find(r => r.rank === 0);
  const rankedFighters = (rankings ?? []).filter(r => r.rank !== null && r.rank > 0).sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0));
  const unrankedFighters = (rankings ?? []).filter(r => r.rank === null);

  return (
    <section className="container flex flex-col gap-8 py-12">
      {/* Header */}
      <header className="space-y-4">
        <Link
          href="/rankings"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          ← Back to all rankings
        </Link>
        <Badge variant="outline" className="w-fit tracking-[0.35em]">
          Rankings
        </Badge>
        <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
          {division}
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>Updated: {new Date(rank_date).toLocaleDateString()}</span>
          <span>•</span>
          <span>{total_fighters} fighters</span>
          <span>•</span>
          <span>Source: FightMatrix</span>
        </div>
      </header>

      {/* Champion */}
      {champion && (
        <Card className="bg-gradient-to-br from-yellow-500/10 to-amber-500/10 border-yellow-500/30">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-yellow-500 to-amber-600 text-2xl font-bold text-white shadow-lg">
                C
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <Badge className="bg-gradient-to-r from-yellow-500 to-amber-600 text-white border-0">
                    {champion.is_interim ? "INTERIM CHAMPION" : "CHAMPION"}
                  </Badge>
                </div>
                <Link
                  href={`/fighters/${champion.fighter_id}`}
                  className="text-2xl font-semibold hover:underline"
                >
                  {champion.fighter_name}
                </Link>
                {champion.nickname && (
                  <p className="text-sm text-muted-foreground">
                    &ldquo;{champion.nickname}&rdquo;
                  </p>
                )}
              </div>
              {champion.rank_movement !== 0 && (
                <Badge
                  variant="default"
                  className={champion.rank_movement > 0 ? "text-sm bg-green-600" : "text-sm bg-red-600"}
                >
                  {champion.rank_movement > 0 ? "↑" : "↓"}
                  {Math.abs(champion.rank_movement)}
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Ranked Fighters */}
      {rankedFighters.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold tracking-tight">Top 15</h2>
          <Card>
            <CardContent className="p-0">
              <ol className="divide-y">
                {rankedFighters.map((entry) => (
                  <li
                    key={entry.ranking_id}
                    className="flex items-center justify-between gap-4 p-4 hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-center gap-4 flex-1 min-w-0">
                      <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-muted text-sm font-semibold">
                        {entry.rank}
                      </span>
                      <div className="flex-1 min-w-0">
                        <Link
                          href={`/fighters/${entry.fighter_id}`}
                          className="font-medium hover:underline block truncate"
                        >
                          {entry.fighter_name}
                        </Link>
                        {entry.nickname && (
                          <p className="text-sm text-muted-foreground truncate">
                            &ldquo;{entry.nickname}&rdquo;
                          </p>
                        )}
                      </div>
                    </div>
                    {entry.rank_movement !== 0 && (
                      <Badge
                        variant="default"
                        className={entry.rank_movement > 0 ? "text-xs flex-shrink-0 bg-green-600" : "text-xs flex-shrink-0 bg-red-600"}
                      >
                        {entry.rank_movement > 0 ? "↑" : "↓"}
                        {Math.abs(entry.rank_movement)}
                      </Badge>
                    )}
                    {entry.rank_movement === 0 && entry.previous_rank !== null && (
                      <Badge variant="outline" className="text-xs flex-shrink-0">
                        —
                      </Badge>
                    )}
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Unranked Fighters (if any) */}
      {unrankedFighters.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold tracking-tight">Not Ranked (NR)</h2>
          <Card>
            <CardContent className="p-0">
              <ul className="divide-y">
                {unrankedFighters.map((entry) => (
                  <li
                    key={entry.ranking_id}
                    className="flex items-center gap-4 p-4 hover:bg-muted/50 transition-colors"
                  >
                    <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted-foreground">
                      NR
                    </span>
                    <div className="flex-1 min-w-0">
                      <Link
                        href={`/fighters/${entry.fighter_id}`}
                        className="font-medium hover:underline block truncate"
                      >
                        {entry.fighter_name}
                      </Link>
                      {entry.nickname && (
                        <p className="text-sm text-muted-foreground truncate">
                          &ldquo;{entry.nickname}&rdquo;
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      )}
    </section>
  );
}
