"use client";

import type { ReactNode } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Props = {
  title: string;
  children: ReactNode;
};

export default function PokedexCard({ title, children }: Props) {
  return (
    <Card className="rounded-3xl border-border bg-card/80">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-0">
        <CardTitle className="text-2xl font-semibold">{title}</CardTitle>
        <span aria-hidden className="h-2 w-12 rounded-full bg-foreground/10" />
      </CardHeader>
      <CardContent className="space-y-4 pt-6">{children}</CardContent>
    </Card>
  );
}
