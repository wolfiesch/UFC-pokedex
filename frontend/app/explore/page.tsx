"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CountryStatsCard } from "@/components/stats/CountryStatsCard";
import { TopGymsWidget } from "@/components/stats/TopGymsWidget";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Globe, MapPin, Dumbbell } from "lucide-react";

export default function ExplorePage() {
  return (
    <div className="container max-w-6xl space-y-8 py-12">
      {/* Page Header */}
      <div className="space-y-2">
        <h1 className="text-4xl font-bold tracking-tight">
          Explore by Location
        </h1>
        <p className="text-lg text-muted-foreground">
          Discover fighters by their birthplace, nationality, and training locations
        </p>
      </div>

      {/* Tabbed Content */}
      <Tabs defaultValue="countries" className="w-full">
        <TabsList className="grid w-full grid-cols-3 lg:w-auto lg:inline-grid">
          <TabsTrigger value="countries" className="flex items-center gap-2">
            <Globe className="h-4 w-4" />
            <span>Countries</span>
          </TabsTrigger>
          <TabsTrigger value="cities" className="flex items-center gap-2">
            <MapPin className="h-4 w-4" />
            <span>Cities</span>
          </TabsTrigger>
          <TabsTrigger value="gyms" className="flex items-center gap-2">
            <Dumbbell className="h-4 w-4" />
            <span>Gyms</span>
          </TabsTrigger>
        </TabsList>

        {/* Countries Tab */}
        <TabsContent value="countries" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Birthplace Countries */}
            <div>
              <CountryStatsCard groupBy="birthplace" minFighters={5} limit={15} />
            </div>

            {/* Nationality Countries */}
            <div>
              <CountryStatsCard groupBy="nationality" minFighters={5} limit={15} />
            </div>
          </div>

          {/* Info Card */}
          <Card className="bg-muted/50">
            <CardHeader>
              <CardTitle className="text-base">About Country Statistics</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-2">
              <p>
                <strong>Birthplace</strong> shows where fighters were born, providing insight
                into global MMA talent distribution.
              </p>
              <p>
                <strong>Nationality</strong> indicates which country a fighter represents in
                competition, which may differ from their birthplace.
              </p>
              <p className="text-xs pt-2">
                Click any country to filter fighters and explore their profiles.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Cities Tab */}
        <TabsContent value="cities" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>City Statistics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-12 space-y-4">
                <MapPin className="h-12 w-12 mx-auto text-muted-foreground/50" />
                <div className="space-y-2">
                  <h3 className="text-lg font-semibold">Coming Soon</h3>
                  <p className="text-sm text-muted-foreground max-w-md mx-auto">
                    City-level statistics will be available once training location data
                    is enriched. Check back soon for insights into MMA hotspots worldwide.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Gyms Tab */}
        <TabsContent value="gyms" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {/* Top Gyms - All */}
            <div className="md:col-span-2 lg:col-span-3">
              <TopGymsWidget minFighters={5} limit={20} />
            </div>
          </div>

          {/* Info Card */}
          <Card className="bg-muted/50">
            <CardHeader>
              <CardTitle className="text-base">About Training Gyms</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-2">
              <p>
                These elite training facilities have produced multiple UFC fighters and
                champions. Training gyms play a crucial role in a fighter's development,
                providing coaching, sparring partners, and technical expertise.
              </p>
              <p className="text-xs pt-2">
                Click any gym to see all fighters who train there.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
