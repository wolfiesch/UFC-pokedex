"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MapPin, Dumbbell, Globe, ArrowRight } from "lucide-react";
import type { FighterDetail } from "@/lib/types";
import CountryFlag from "@/components/CountryFlag";
import { toCountryIsoCode } from "@/lib/countryCodes";

interface FighterLocationCardProps {
  fighter: FighterDetail;
}

export function FighterLocationCard({ fighter }: FighterLocationCardProps) {
  const {
    birthplace,
    birthplace_country: birthplaceCountry,
    training_gym: trainingGym,
    training_city: trainingCity,
    training_country: trainingCountry,
    nationality,
  } = fighter;

  const birthplaceFlag = toCountryIsoCode(
    birthplaceCountry ?? nationality ?? undefined,
  );
  const nationalityFlag = toCountryIsoCode(nationality ?? undefined);
  const trainingFlag = toCountryIsoCode(
    trainingCountry ?? nationality ?? undefined,
  );

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
            <div className="space-y-2 pl-6">
              <div className="flex items-center gap-2">
                {birthplaceFlag && (
                  <CountryFlag
                    countryCode={birthplaceFlag}
                    width={24}
                    height={16}
                  />
                )}
                <Badge variant="outline" className="text-base">
                  {birthplace}
                </Badge>
              </div>
              {birthplaceCountry && (
                <div className="flex items-center gap-2">
                  <Link
                    href={`/?birthplace_country=${encodeURIComponent(birthplaceCountry)}`}
                    className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
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
            <div className="space-y-2 pl-6">
              <Badge variant="outline" className="text-base">
                {nationality}
              </Badge>
              <div className="flex items-center gap-2">
                <Link
                  href={`/?nationality=${encodeURIComponent(nationality)}`}
                  className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
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
            <div className="space-y-2 pl-6">
              <div className="flex items-center gap-2">
                {trainingFlag && (
                  <CountryFlag
                    countryCode={trainingFlag}
                    width={24}
                    height={16}
                  />
                )}
                <div className="flex flex-col gap-1">
                  <Badge variant="secondary" className="w-fit text-base">
                    {trainingGym}
                  </Badge>
                  {(trainingCity || trainingCountry) && (
                    <span className="text-sm text-muted-foreground">
                      {[trainingCity, trainingCountry]
                        .filter(Boolean)
                        .join(", ")}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Link
                  href={`/?training_gym=${encodeURIComponent(trainingGym)}`}
                  className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
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
          <div className="border-t border-border/50 pt-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Represents</span>
              <div className="flex items-center gap-2">
                {nationalityFlag && (
                  <CountryFlag
                    countryCode={nationalityFlag}
                    width={20}
                    height={14}
                  />
                )}
                <Badge variant="outline">{nationality}</Badge>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
