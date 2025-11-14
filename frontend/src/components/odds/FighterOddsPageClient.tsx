"use client";

import { useEffect, useMemo, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { useFighterOddsChart, useFighterOddsHistory } from "@/hooks/useOddsData";
import { FighterOddsChart } from "./FighterOddsChart";
import { FightSelector } from "./FightSelector";
import { OddsHistoryTable } from "./OddsHistoryTable";

type FighterOddsPageClientProps = {
  fighterId: string;
};

export function FighterOddsPageClient({
  fighterId,
}: FighterOddsPageClientProps) {
  const [selectedFightId, setSelectedFightId] = useState<string>();

  const {
    data: chartData,
    isLoading: chartLoading,
    error: chartError,
  } = useFighterOddsChart(fighterId);
  const {
    data: historyData,
    isLoading: historyLoading,
    error: historyError,
  } = useFighterOddsHistory(fighterId);

  const fights = useMemo(
    () => chartData?.fights ?? [],
    [chartData?.fights],
  );

  useEffect(() => {
    if (!selectedFightId && fights.length) {
      setSelectedFightId(fights[0].fight_id);
    }
  }, [fights, selectedFightId]);

  const totalFights = historyData?.total_fights ?? 0;
  const avgPoints = useMemo(() => {
    if (!historyData?.odds_history?.length) return 0;
    const totalPoints = historyData.odds_history.reduce(
      (sum, fight) => sum + fight.num_odds_points,
      0,
    );
    return Math.round(totalPoints / historyData.odds_history.length);
  }, [historyData]);

  const showEmptyState =
    !chartLoading && !historyLoading && !chartData?.fights?.length;

  return (
    <section className="space-y-8">
      {(chartError || historyError) && (
        <Alert variant="destructive">
          <AlertTitle>Unable to load odds</AlertTitle>
          <AlertDescription>
            {(chartError || historyError)?.message ??
              "Please retry in a moment."}
          </AlertDescription>
        </Alert>
      )}

      {showEmptyState ? (
        <Card className="bg-card/60">
          <CardHeader>
            <CardTitle>Betting Odds</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              We don&apos;t have betting odds for this fighter yet. Once the
              next scraper run completes the data will appear here.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-8 lg:grid-cols-[2fr,1fr]">
          {chartLoading ? (
            <Skeleton className="h-96 rounded-2xl" />
          ) : (
            <FighterOddsChart
              fights={fights}
              selectedFightId={selectedFightId}
            />
          )}
          <Card className="bg-card/60">
            <CardHeader>
              <CardTitle>Fights</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {chartLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-16 rounded-xl" />
                  <Skeleton className="h-16 rounded-xl" />
                  <Skeleton className="h-16 rounded-xl" />
                </div>
              ) : (
                <FightSelector
                  fights={fights}
                  selectedId={selectedFightId}
                  onSelect={setSelectedFightId}
                />
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <Card className="bg-card/60">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <CardTitle>Odds History</CardTitle>
            <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
              {totalFights} fights · avg {avgPoints} points
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {historyLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-12 rounded-xl" />
              <Skeleton className="h-12 rounded-xl" />
              <Skeleton className="h-12 rounded-xl" />
            </div>
          ) : (
            <OddsHistoryTable history={historyData?.odds_history ?? []} />
          )}
        </CardContent>
      </Card>
    </section>
  );
}
