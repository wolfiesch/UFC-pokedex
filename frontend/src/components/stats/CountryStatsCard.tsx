"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import client from "@/lib/api-client";
import { Flag, Loader2 } from "lucide-react";

interface CountryStat {
  country: string;
  count: number;
  percentage: number;
}

interface CountryStatsCardProps {
  groupBy?: "birthplace" | "nationality";
  minFighters?: number;
  limit?: number;
}

export function CountryStatsCard({
  groupBy = "birthplace",
  minFighters = 5,
  limit = 10,
}: CountryStatsCardProps) {
  const [stats, setStats] = useState<CountryStat[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchStats() {
      try {
        setIsLoading(true);
        setError(null);

        const { data, error: apiError } = await client.GET("/stats/countries", {
          params: {
            query: {
              group_by: groupBy,
              min_fighters: minFighters,
            },
          },
        });

        if (apiError) {
          setError("Failed to load country statistics");
          return;
        }

        if (data && data.countries) {
          // Limit to top N countries
          setStats(data.countries.slice(0, limit));
        }
      } catch (err) {
        console.error("Error fetching country stats:", err);
        setError("An error occurred while loading data");
      } finally {
        setIsLoading(false);
      }
    }

    fetchStats();
  }, [groupBy, minFighters, limit]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Flag className="h-5 w-5" />
          Top Countries{" "}
          {groupBy === "birthplace" ? "(by Birthplace)" : "(by Nationality)"}
        </CardTitle>
      </CardHeader>
      <CardContent className="min-h-[360px]">
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: limit }).map((_, index) => (
              <div
                key={index}
                className="flex items-center justify-between rounded-md border border-border/50 p-3"
              >
                <div className="flex items-center gap-3">
                  <Skeleton className="h-8 w-8 rounded-full" />
                  <div className="space-y-2">
                    <Skeleton className="h-3 w-32" />
                    <Skeleton className="h-3 w-20" />
                  </div>
                </div>
                <Skeleton className="h-6 w-20 rounded-full" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="py-8 text-center">
            <p className="text-sm text-muted-foreground">{error}</p>
          </div>
        ) : stats && stats.length > 0 ? (
          <div className="space-y-3">
            {stats.map((stat, index) => (
              <Link
                key={stat.country}
                href={`/?${groupBy === "birthplace" ? "birthplace_country" : "nationality"}=${encodeURIComponent(stat.country)}`}
                className="flex items-center justify-between rounded-md p-2 transition-colors hover:bg-accent"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">
                    #{index + 1}
                  </div>
                  <div>
                    <div className="font-semibold">{stat.country}</div>
                    <div className="text-xs text-muted-foreground">
                      {stat.percentage.toFixed(1)}% of roster
                    </div>
                  </div>
                </div>
                <Badge variant="secondary">{stat.count} fighters</Badge>
              </Link>
            ))}
          </div>
        ) : (
          <div className="py-8 text-center">
            <p className="text-sm text-muted-foreground">No data available</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
