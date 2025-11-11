"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MapPin, Dumbbell, Globe, ArrowRight } from "lucide-react";
import type { FighterDetail } from "@/lib/types";

interface FighterLocationCardProps {
  fighter: FighterDetail;
}

export function FighterLocationCard({ fighter }: FighterLocationCardProps) {
  const birthplace = (fighter as any).birthplace;
  const birthplaceCountry = (fighter as any).birthplace_country;
  const trainingGym = (fighter as any).training_gym;
  const trainingCity = (fighter as any).training_city;
  const trainingCountry = (fighter as any).training_country;
  const nationality = (fighter as any).nationality;

  // Don't show the card if no location data exists
  if (!birthplace && !trainingGym && !nationality) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Globe className="h-5 w-5" />
          Location Information
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Birthplace */}
        {birthplace && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              <MapPin className="h-4 w-4" />
              Birthplace
            </div>
            <div className="pl-6 space-y-2">
              <Badge variant="outline" className="text-base">
                {birthplace}
              </Badge>
              {birthplaceCountry && (
                <div className="flex items-center gap-2">
                  <Link
                    href={`/?birthplace_country=${encodeURIComponent(birthplaceCountry)}`}
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    View all fighters from {birthplaceCountry}
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Nationality (if different from birthplace or no birthplace) */}
        {nationality && !birthplace && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              <Globe className="h-4 w-4" />
              Nationality
            </div>
            <div className="pl-6 space-y-2">
              <Badge variant="outline" className="text-base">
                {nationality}
              </Badge>
              <div className="flex items-center gap-2">
                <Link
                  href={`/?nationality=${encodeURIComponent(nationality)}`}
                  className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                >
                  View all {nationality} fighters
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            </div>
          </div>
        )}

        {/* Training Gym */}
        {trainingGym && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              <Dumbbell className="h-4 w-4" />
              Training
            </div>
            <div className="pl-6 space-y-2">
              <div className="flex flex-col gap-1">
                <Badge variant="secondary" className="text-base w-fit">
                  {trainingGym}
                </Badge>
                {(trainingCity || trainingCountry) && (
                  <span className="text-sm text-muted-foreground">
                    {[trainingCity, trainingCountry].filter(Boolean).join(", ")}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Link
                  href={`/?training_gym=${encodeURIComponent(trainingGym)}`}
                  className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                >
                  View all fighters from {trainingGym}
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            </div>
          </div>
        )}

        {/* Additional Info: Nationality if birthplace exists */}
        {nationality && birthplace && nationality !== birthplaceCountry && (
          <div className="pt-2 border-t border-border/50">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Represents</span>
              <Badge variant="outline">{nationality}</Badge>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
