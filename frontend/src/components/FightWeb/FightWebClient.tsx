"use client";

import {
  useCallback,
  useMemo,
  useRef,
  useState,
} from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getFightGraph } from "@/lib/api";
import type {
  FightGraphQueryParams,
  FightGraphResponse,
} from "@/lib/types";

import { FightGraphCanvas } from "./FightGraphCanvas";
import { FightWebFilters } from "./FightWebFilters";
import { deriveEventYearBounds } from "./graph-layout";
import { clampLimit, normalizeFilters } from "./filter-utils";

type FightWebClientProps = {
  initialData: FightGraphResponse | null;
  initialFilters?: FightGraphQueryParams;
  initialError?: string | null;
};

function formatNumber(value: number): string {
  return value.toLocaleString("en-US");
}

function filtersEqual(
  a: FightGraphQueryParams,
  b: FightGraphQueryParams
): boolean {
  return (
    (a.division ?? null) === (b.division ?? null) &&
    (a.startYear ?? null) === (b.startYear ?? null) &&
    (a.endYear ?? null) === (b.endYear ?? null) &&
    clampLimit(a.limit ?? null) === clampLimit(b.limit ?? null) &&
    Boolean(a.includeUpcoming) === Boolean(b.includeUpcoming)
  );
}

function buildDivisionList(data: FightGraphResponse | null): string[] {
  if (!data) {
    return [];
  }
  const divisions = new Set<string>();
  for (const node of data.nodes) {
    if (node.division && node.division.trim().length > 0) {
      divisions.add(node.division.trim());
    }
  }
  return Array.from(divisions);
}

export function FightWebClient({
  initialData,
  initialFilters,
  initialError,
}: FightWebClientProps) {
  const fallbackLimit = useMemo(
    () =>
      clampLimit(
        initialFilters?.limit ??
          initialData?.nodes.length ??
          150
      ),
    [initialData?.nodes.length, initialFilters?.limit]
  );

  const defaultFilters = useMemo(
    () =>
      normalizeFilters(
        {
          division: initialFilters?.division ?? null,
          startYear: initialFilters?.startYear ?? null,
          endYear: initialFilters?.endYear ?? null,
          limit: fallbackLimit,
          includeUpcoming: initialFilters?.includeUpcoming ?? false,
        },
        fallbackLimit
      ),
    [
      fallbackLimit,
      initialFilters?.division,
      initialFilters?.endYear,
      initialFilters?.includeUpcoming,
      initialFilters?.startYear,
    ]
  );

  const [graphData, setGraphData] = useState<FightGraphResponse | null>(
    initialData
  );
  const [appliedFilters, setAppliedFilters] =
    useState<FightGraphQueryParams>(defaultFilters);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(initialError ?? null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const requestIdRef = useRef(0);

  const applyFilters = useCallback(
    async (nextFilters: FightGraphQueryParams) => {
      const normalized = normalizeFilters(
        nextFilters,
        nextFilters.limit ?? defaultFilters.limit ?? fallbackLimit
      );

      requestIdRef.current += 1;
      const currentRequest = requestIdRef.current;

      setIsLoading(true);
      setError(null);

      try {
        const result = await getFightGraph(normalized);
        if (currentRequest !== requestIdRef.current) {
          return;
        }
        setGraphData(result);
        setAppliedFilters(normalized);
        setSelectedNodeId(null);
      } catch (caught) {
        if (currentRequest !== requestIdRef.current) {
          return;
        }
        setError(
          caught instanceof Error
            ? caught.message
            : "Unable to refresh the FightWeb graph."
        );
      } finally {
        if (currentRequest === requestIdRef.current) {
          setIsLoading(false);
        }
      }
    },
    [defaultFilters.limit, fallbackLimit]
  );

  const handleReset = useCallback(() => {
    if (filtersEqual(appliedFilters, defaultFilters)) {
      setSelectedNodeId(null);
      return;
    }
    void applyFilters(defaultFilters);
  }, [appliedFilters, applyFilters, defaultFilters]);

  const nodeCount = graphData?.nodes.length ?? 0;
  const linkCount = graphData?.links.length ?? 0;

  const activeDivision =
    appliedFilters.division && appliedFilters.division.trim().length > 0
      ? appliedFilters.division
      : "All divisions";

  const timeRangeLabel = useMemo(() => {
    const start = appliedFilters.startYear ?? null;
    const end = appliedFilters.endYear ?? null;
    if (start && end) {
      return `${start} – ${end}`;
    }
    if (start) {
      return `${start} onward`;
    }
    if (end) {
      return `≤ ${end}`;
    }
    return "All time";
  }, [appliedFilters.endYear, appliedFilters.startYear]);

  const availableDivisions = useMemo(
    () => buildDivisionList(graphData),
    [graphData]
  );

  const eventYearBounds = useMemo(
    () => deriveEventYearBounds(graphData),
    [graphData]
  );

  const nodeById = useMemo(() => {
    if (!graphData) {
      return new Map<string, FightGraphResponse["nodes"][number]>();
    }
    return new Map(
      graphData.nodes.map((node) => [node.fighter_id, node])
    );
  }, [graphData]);

  const selectedConnections = useMemo(() => {
    if (!graphData || !selectedNodeId) {
      return [];
    }
    const connections = graphData.links
      .filter(
        (link) =>
          link.source === selectedNodeId || link.target === selectedNodeId
      )
      .map((link) => {
        const counterpartId =
          link.source === selectedNodeId ? link.target : link.source;
        const fighter = nodeById.get(counterpartId);
        return {
          fighter,
          link,
        };
      })
      .filter(
        (entry): entry is { fighter: FightGraphResponse["nodes"][number]; link: FightGraphResponse["links"][number] } =>
          Boolean(entry.fighter)
      )
      .sort((a, b) => b.link.fights - a.link.fights)
      .slice(0, 6);

    return connections;
  }, [graphData, nodeById, selectedNodeId]);

  const selectedNode = useMemo(() => {
    if (!graphData || !selectedNodeId) {
      return null;
    }
    return nodeById.get(selectedNodeId) ?? null;
  }, [graphData, nodeById, selectedNodeId]);

  return (
    <div className="space-y-8">
      {error ? (
        <div
          className="rounded-3xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive-foreground"
          role="alert"
        >
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle>Indexed Fighters</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-3xl font-semibold tracking-tight">
            {formatNumber(nodeCount)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Fight Connections</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-3xl font-semibold tracking-tight">
            {formatNumber(linkCount)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Division Scope</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-lg text-muted-foreground">
            {activeDivision}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Time Window</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-lg text-muted-foreground">
            {timeRangeLabel}
            <div className="mt-1 text-xs uppercase tracking-[0.3em] text-muted-foreground/80">
              Limit {formatNumber(appliedFilters.limit ?? fallbackLimit)}
              {" • "}
              {appliedFilters.includeUpcoming
                ? "Upcoming included"
                : "Upcoming excluded"}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-[320px,1fr]">
        <div className="space-y-4">
          <FightWebFilters
            filters={appliedFilters}
            onApply={applyFilters}
            onReset={handleReset}
            availableDivisions={availableDivisions}
            yearBounds={eventYearBounds}
            isLoading={isLoading}
          />

          {selectedNode ? (
            <Card className="border border-border/80 bg-card">
              <CardHeader>
                <CardTitle>{selectedNode.name}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-muted-foreground">
                <div className="flex items-center justify-between">
                  <span className="uppercase tracking-[0.3em] text-muted-foreground/80">
                    Record
                  </span>
                  <span>{selectedNode.record ?? "Unknown"}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="uppercase tracking-[0.3em] text-muted-foreground/80">
                    Division
                  </span>
                  <span>{selectedNode.division ?? "Unlisted"}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="uppercase tracking-[0.3em] text-muted-foreground/80">
                    Total fights
                  </span>
                  <span>{formatNumber(selectedNode.total_fights)}</span>
                </div>
                {selectedConnections.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground/80">
                      Key connections
                    </div>
                    <ul className="space-y-2 text-sm">
                      {selectedConnections.map(({ fighter, link }) => (
                        <li
                          key={`${selectedNode.fighter_id}-${fighter.fighter_id}`}
                          className="flex items-center justify-between rounded-2xl border border-border/70 bg-background/50 px-3 py-2"
                        >
                          <span className="text-foreground/90">
                            {fighter.name}
                          </span>
                          <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
                            {link.fights} fights
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    Select a connected fighter in the graph to explore rivalries.
                  </p>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card className="border border-dashed border-border/60 bg-card/40">
              <CardHeader>
                <CardTitle>Inspect fighters</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Click a node in the graph to reveal fighter details and top
                connections here.
              </CardContent>
            </Card>
          )}
        </div>

        <FightGraphCanvas
          data={graphData}
          isLoading={isLoading}
          selectedNodeId={selectedNodeId}
          onSelectNode={setSelectedNodeId}
        />
      </div>
    </div>
  );
}
