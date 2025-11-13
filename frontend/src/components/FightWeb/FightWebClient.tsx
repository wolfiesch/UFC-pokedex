"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getFightGraph } from "@/lib/api";
import type { FightGraphQueryParams, FightGraphResponse } from "@/lib/types";

import { FightGraphCanvas } from "./FightGraphCanvas";
import { FightWebFilters } from "./FightWebFilters";
import { FightWebInsightsPanel } from "./FightWebInsightsPanel";
import { FightWebLegend } from "./FightWebLegend";
import { FightWebSearch } from "./FightWebSearch";
import { FightWebSelectedFighter } from "./FightWebSelectedFighter";
import { FightWebSummary } from "./FightWebSummary";
import { clampLimit, normalizeFilters } from "./filter-utils";
import { extractFightWebInsights } from "./insight-utils";
import {
  createDivisionColorScale,
  createRecencyColorScale,
  DEFAULT_NODE_COLOR,
  deriveEventYearBounds,
} from "./graph-layout";

type FightWebClientProps = {
  initialData: FightGraphResponse | null;
  initialFilters?: FightGraphQueryParams;
  initialError?: string | null;
};

function filtersEqual(
  a: FightGraphQueryParams,
  b: FightGraphQueryParams,
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
    () => clampLimit(initialFilters?.limit ?? initialData?.nodes.length ?? 150),
    [initialData?.nodes.length, initialFilters?.limit],
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
        fallbackLimit,
      ),
    [
      fallbackLimit,
      initialFilters?.division,
      initialFilters?.endYear,
      initialFilters?.includeUpcoming,
      initialFilters?.startYear,
    ],
  );

  const [graphData, setGraphData] = useState<FightGraphResponse | null>(
    initialData,
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
        nextFilters.limit ?? defaultFilters.limit ?? fallbackLimit,
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
            : "Unable to refresh the FightWeb graph.",
        );
      } finally {
        if (currentRequest === requestIdRef.current) {
          setIsLoading(false);
        }
      }
    },
    [defaultFilters.limit, fallbackLimit],
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

  const availableDivisions = useMemo(
    () => buildDivisionList(graphData),
    [graphData],
  );

  const eventYearBounds = useMemo(
    () => deriveEventYearBounds(graphData),
    [graphData],
  );

  const palette = useMemo(() => {
    if (!graphData) {
      return new Map<string, string>();
    }
    return createDivisionColorScale(graphData.nodes);
  }, [graphData]);

  // Detect if we're filtered to a single division
  const isSingleDivision = useMemo(() => {
    if (!appliedFilters.division || !graphData) {
      return false;
    }

    const filterDivision = appliedFilters.division.trim();
    if (filterDivision.length === 0) {
      return false;
    }

    // Check if all nodes (with divisions) match the filter
    const nodesWithDivision = graphData.nodes.filter(
      (node) => node.division && node.division.trim().length > 0,
    );

    if (nodesWithDivision.length === 0) {
      return false;
    }

    // All nodes should match the filtered division
    return nodesWithDivision.every(
      (node) => node.division?.trim() === filterDivision,
    );
  }, [appliedFilters.division, graphData]);

  // Create recency-based color map when single division is detected
  const nodeColorMap = useMemo(() => {
    if (!isSingleDivision || !graphData || !appliedFilters.division) {
      return null;
    }

    // Get the division's base color from the palette
    const divisionColor =
      palette.get(appliedFilters.division.trim()) ?? DEFAULT_NODE_COLOR;

    // Create recency-based color scale
    return createRecencyColorScale(graphData.nodes, divisionColor);
  }, [isSingleDivision, graphData, appliedFilters.division, palette]);

  const insights = useMemo(
    () => extractFightWebInsights(graphData),
    [graphData],
  );

  const nodeById = useMemo(() => {
    if (!graphData) {
      return new Map<string, FightGraphResponse["nodes"][number]>();
    }
    return new Map(graphData.nodes.map((node) => [node.fighter_id, node]));
  }, [graphData]);

  useEffect(() => {
    if (!selectedNodeId) {
      return;
    }
    if (!nodeById.has(selectedNodeId)) {
      setSelectedNodeId(null);
    }
  }, [nodeById, selectedNodeId]);

  const selectedConnections = useMemo(() => {
    if (!graphData || !selectedNodeId) {
      return [];
    }
    const connections = graphData.links
      .filter(
        (link) =>
          link.source === selectedNodeId || link.target === selectedNodeId,
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
        (
          entry,
        ): entry is {
          fighter: FightGraphResponse["nodes"][number];
          link: FightGraphResponse["links"][number];
        } => Boolean(entry.fighter),
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

  const handleSelectFighter = useCallback(
    (fighterId: string) => {
      if (!fighterId) {
        setSelectedNodeId(null);
        return;
      }
      if (nodeById.has(fighterId)) {
        setSelectedNodeId(fighterId);
      }
    },
    [nodeById],
  );

  return (
    <div className="space-y-10">
      {error ? (
        <div
          className="rounded-3xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive-foreground"
          role="alert"
        >
          {error}
        </div>
      ) : null}

      <FightWebSummary
        nodeCount={nodeCount}
        linkCount={linkCount}
        filters={appliedFilters}
        fallbackLimit={fallbackLimit}
        insights={insights}
      />

      <div className="grid gap-6 xl:grid-cols-[360px,1fr]">
        <div className="space-y-6">
          <FightWebFilters
            filters={appliedFilters}
            onApply={applyFilters}
            onReset={handleReset}
            availableDivisions={availableDivisions}
            yearBounds={eventYearBounds}
            isLoading={isLoading}
          />

          <FightWebSearch
            nodes={graphData?.nodes ?? []}
            onSelect={handleSelectFighter}
            onClear={() => setSelectedNodeId(null)}
          />

          <FightWebInsightsPanel
            insights={insights}
            onSelectFighter={handleSelectFighter}
          />

          <FightWebLegend
            palette={palette}
            breakdown={insights.divisionBreakdown}
          />
        </div>

        <div className="space-y-6">
          <FightGraphCanvas
            data={graphData}
            isLoading={isLoading}
            selectedNodeId={selectedNodeId}
            onSelectNode={setSelectedNodeId}
            palette={palette}
            nodeColorMap={nodeColorMap}
          />

          <FightWebSelectedFighter
            selectedNode={selectedNode}
            connections={selectedConnections}
          />
        </div>
      </div>
    </div>
  );
}
