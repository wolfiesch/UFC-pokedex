"use client";

import type { FightGraphResponse } from "@/lib/types";

type FightGraphCanvasProps = {
  data: FightGraphResponse | null;
};

export function FightGraphCanvas({ data }: FightGraphCanvasProps) {
  const hasEdges = (data?.links?.length ?? 0) > 0;
  const hasNodes = (data?.nodes?.length ?? 0) > 0;

  return (
    <div className="flex h-[520px] w-full flex-col rounded-3xl border border-dashed border-border/60 bg-muted/10 p-6">
      <div className="flex items-center justify-between text-xs uppercase tracking-[0.3em] text-muted-foreground/90">
        <span>FightWeb Graph</span>
        <span>
          {hasNodes ? `${data?.nodes.length ?? 0} fighters` : "No fighters"}
          {" • "}
          {hasEdges ? `${data?.links.length ?? 0} links` : "No connections"}
        </span>
      </div>
      <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-muted-foreground">
        {hasNodes ? (
          <span>Interactive fight network visualization is loading in the next iteration.</span>
        ) : (
          <span>We could not find sufficient data to construct the fight network yet.</span>
        )}
      </div>
    </div>
  );
}
