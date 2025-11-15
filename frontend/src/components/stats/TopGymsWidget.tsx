"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { FighterLinkList } from "@/components/fighter/FighterLinkList";
import { Dumbbell } from "lucide-react";
import client from "@/lib/api-client";

interface GymStat {
  gym: string;
  city?: string | null;
  country?: string | null;
  fighter_count: number;
  notable_fighters?:
    | string[]
    | Array<{
        fighter_id?: string | null;
        fighter_name: string;
      }>;
}

interface TopGymsWidgetProps {
  minFighters?: number;
  sortBy?: "fighters" | "name";
  limit?: number;
}

export function TopGymsWidget({
  minFighters = 10,
  sortBy = "fighters",
  limit = 5,
}: TopGymsWidgetProps) {
  const [gyms, setGyms] = useState<GymStat[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchGyms() {
      try {
        setIsLoading(true);
        setError(null);

        const { data, error: apiError } = await client.GET("/stats/gyms", {
          params: {
            query: {
              min_fighters: minFighters,
              sort_by: sortBy,
            },
          },
        });

        if (apiError) {
          setError("Failed to load gym statistics");
          return;
        }

        if (data && data.gyms) {
          // Limit to top N gyms
          setGyms(data.gyms.slice(0, limit));
        }
      } catch (err) {
        console.error("Error fetching gym stats:", err);
        setError("An error occurred while loading data");
      } finally {
        setIsLoading(false);
      }
    }

    fetchGyms();
  }, [minFighters, sortBy, limit]);

  const getGymInitials = (gymName: string): string => {
    const words = gymName.split(" ");
    if (words.length === 1) {
      return gymName.substring(0, 2).toUpperCase();
    }
    return words
      .slice(0, 2)
      .map((word) => word[0])
      .join("")
      .toUpperCase();
  };

  const getNotableFighters = (gym: GymStat) => {
    const fighters = gym.notable_fighters ?? [];
    if (!fighters.length) {
      return [];
    }
    if (typeof fighters[0] === "string") {
      return (fighters as string[]).map((name) => ({
        fighterId: null,
        name,
      }));
    }
    return (fighters as Array<{ fighter_id?: string | null; fighter_name: string }>).map(
      (fighter) => ({
        fighterId: fighter.fighter_id ?? null,
        name: fighter.fighter_name,
      }),
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Dumbbell className="h-5 w-5" />
          Elite Training Gyms
        </CardTitle>
      </CardHeader>
      <CardContent className="min-h-[360px]">
        {isLoading ? (
          <div className="space-y-4">
            {Array.from({ length: limit }).map((_, index) => (
              <div
                key={index}
                className="flex items-start gap-3 rounded-md border border-border/60 p-3"
              >
                <Skeleton className="h-12 w-12 rounded-full" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-44" />
                  <Skeleton className="h-3 w-32" />
                  <Skeleton className="h-3 w-24" />
                </div>
                <Skeleton className="h-5 w-12 rounded-full" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="py-8 text-center">
            <p className="text-sm text-muted-foreground">{error}</p>
          </div>
        ) : gyms && gyms.length > 0 ? (
          <div className="space-y-4">
            {gyms.map((gym) => (
              <Link
                key={gym.gym}
                href={`/?training_gym=${encodeURIComponent(gym.gym)}`}
                className="flex items-start gap-3 rounded-md p-2 transition-colors hover:bg-accent"
              >
                <Avatar className="h-12 w-12">
                  <AvatarFallback className="bg-gradient-to-br from-primary/20 to-primary/10 font-bold text-primary">
                    {getGymInitials(gym.gym)}
                  </AvatarFallback>
                </Avatar>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-semibold">{gym.gym}</div>
                  {(gym.city || gym.country) && (
                    <div className="text-sm text-muted-foreground">
                      {[gym.city, gym.country].filter(Boolean).join(", ")}
                    </div>
                  )}
                  <div className="mt-1 text-xs text-muted-foreground">
                    {gym.fighter_count} fighter
                    {gym.fighter_count !== 1 ? "s" : ""}
                  </div>
                  {getNotableFighters(gym).length > 0 ? (
                    <FighterLinkList
                      fighters={getNotableFighters(gym).slice(0, 3)}
                      className="mt-1 text-xs text-primary"
                    />
                  ) : null}
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="py-8 text-center">
            <p className="text-sm text-muted-foreground">No gyms found</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
