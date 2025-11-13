"use client";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type PeakRankingProps = {
  fighterName: string;
  division: string;
  peakRank: number;
  rankDate: string;
  isInterim: boolean;
  source: string;
};

export default function PeakRanking({
  fighterName,
  division,
  peakRank,
  rankDate,
  isInterim,
  source,
}: PeakRankingProps) {
  const isChampion = peakRank === 0;
  const formattedDate = new Date(rankDate).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return (
    <Card
      className={
        isChampion
          ? "border-yellow-500/30 bg-gradient-to-br from-yellow-500/10 to-amber-500/10"
          : ""
      }
    >
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <svg
            className="h-5 w-5 text-yellow-500"
            fill="currentColor"
            viewBox="0 0 20 20"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
          Peak Ranking
        </CardTitle>
        <CardDescription>{division}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-baseline gap-2">
          <span className="text-5xl font-bold">
            {isChampion ? "C" : `#${peakRank}`}
          </span>
          {isChampion && (
            <Badge className="border-0 bg-gradient-to-r from-yellow-500 to-amber-600 text-white">
              {isInterim ? "INTERIM CHAMPION" : "CHAMPION"}
            </Badge>
          )}
        </div>
        <div className="space-y-1 text-sm text-muted-foreground">
          <p>Achieved: {formattedDate}</p>
          <p>Source: {source.toUpperCase()}</p>
        </div>
        {isChampion && (
          <p className="text-sm font-medium text-foreground">
            {fighterName} reached the pinnacle of the {division} division.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
