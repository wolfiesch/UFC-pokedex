"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { useFightGraph } from "@/hooks/useFightGraph";
import type { FightGraphQueryParams, FightGraphResponse } from "@/lib/types";

import { FightGraphCanvas } from "./FightGraphCanvas";
import { FightWebFilters } from "./FightWebFilters";
import { FightWebInsightsPanel } from "./FightWebInsightsPanel";
import { FightWebLegend } from "./FightWebLegend";
import { FightWebSearch } from "./FightWebSearch";
import { FightWebSelectedFighter } from "./FightWebSelectedFighter";
import { FightWebSummary } from "./FightWebSummary";
import { clampLimit, filtersEqual, normalizeFilters } from "./filter-utils";
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

const SEARCH_PARAM_KEYS = {
  division: "division",
  startYear: "startYear",
  endYear: "endYear",
  limit: "limit",
  includeUpcoming: "upcoming",
} as const;

/**
 * Parse the current URL query string into a set of fight graph filters. The
 * defaults are applied first so that missing parameters gracefully fall back
 * to the server-provided initial state.
 */
function parseFiltersFromQueryString(
  queryString: string,
  defaults: FightGraphQueryParams
): FightGraphQueryParams {
  const params = new URLSearchParams(queryString);

  const base: FightGraphQueryParams = {
    division: defaults.division ?? null,
    startYear: defaults.startYear ?? null,
    endYear: defaults.endYear ?? null,
    limit: defaults.limit ?? null,
    includeUpcoming: defaults.includeUpcoming ?? false,
  };

  const divisionParam = params.get(SEARCH_PARAM_KEYS.division);
  if (divisionParam !== null) {
    base.division = divisionParam.trim().length > 0 ? divisionParam : null;
  }

  const parseNumber = (value: string | null): number | null => {
    if (value === null) {
      return null;
    }
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : null;
  };

  if (params.has(SEARCH_PARAM_KEYS.startYear)) {
    base.startYear = parseNumber(params.get(SEARCH_PARAM_KEYS.startYear));
  }

  if (params.has(SEARCH_PARAM_KEYS.endYear)) {
    base.endYear = parseNumber(params.get(SEARCH_PARAM_KEYS.endYear));
  }

  if (params.has(SEARCH_PARAM_KEYS.limit)) {
    base.limit = parseNumber(params.get(SEARCH_PARAM_KEYS.limit));
  }

  if (params.has(SEARCH_PARAM_KEYS.includeUpcoming)) {
    const raw = params.get(SEARCH_PARAM_KEYS.includeUpcoming);
    if (!raw) {
      base.includeUpcoming = defaults.includeUpcoming ?? false;
    } else {
      const normalized = raw.toLowerCase();
      if (normalized === "1" || normalized === "true" || normalized === "yes") {
        base.includeUpcoming = true;
      } else if (
        normalized === "0" || normalized === "false" || normalized === "no"
      ) {
        base.includeUpcoming = false;
      }
    }
  }

  return base;
}

/**
 * Serialize normalised fight graph filters into URLSearchParams so the router
 * can update the address bar without manual string concatenation.
 */
function createSearchParamsFromFilters(
  filters: FightGraphQueryParams
): URLSearchParams {
  const params = new URLSearchParams();

  if (filters.division && filters.division.trim().length > 0) {
    params.set(SEARCH_PARAM_KEYS.division, filters.division.trim());
  }

  if (typeof filters.startYear === "number") {
    params.set(SEARCH_PARAM_KEYS.startYear, String(filters.startYear));
  }

  if (typeof filters.endYear === "number") {
    params.set(SEARCH_PARAM_KEYS.endYear, String(filters.endYear));
  }

  if (typeof filters.limit === "number") {
    params.set(SEARCH_PARAM_KEYS.limit, String(filters.limit));
  }

  if (filters.includeUpcoming) {
    params.set(SEARCH_PARAM_KEYS.includeUpcoming, "true");
  }

  return params;
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
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

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

  const rawSearchParams = searchParams.toString();
  const derivedFilters = useMemo(
    () => parseFiltersFromQueryString(rawSearchParams, defaultFilters),
    [rawSearchParams, defaultFilters],
  );

  const appliedFilters = useMemo(
    () => normalizeFilters(derivedFilters, fallbackLimit),
    [derivedFilters, fallbackLimit],
  );

  const hydratedInitialData = useMemo(() => {
    if (!initialData) {
      return null;
    }
    return filtersEqual(appliedFilters, defaultFilters) ? initialData : null;
  }, [appliedFilters, defaultFilters, initialData]);

  const { data, status, error: queryError, refetch, isFetching } = useFightGraph(
    appliedFilters,
    { initialData: hydratedInitialData },
  );

  const graphData = data ?? null;
  const isLoading = status === "pending" && !graphData;
  const isRefreshing = isFetching && !isLoading;

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const previousFiltersRef = useRef<FightGraphQueryParams>(appliedFilters);
  useEffect(() => {
    if (!filtersEqual(previousFiltersRef.current, appliedFilters)) {
      previousFiltersRef.current = appliedFilters;
      setSelectedNodeId(null);
    }
  }, [appliedFilters]);

  const [sidebarError, setSidebarError] = useState<string | null>(
    initialError ?? null,
  );
  const initialErrorRef = useRef<string | null>(initialError ?? null);
  const lastToastMessageRef = useRef<string | null>(null);

  useEffect(() => {
    if (initialErrorRef.current) {
      const message = initialErrorRef.current;
      toast.error(message, {
        duration: 6000,
        action: {
          label: "Retry",
          onClick: () => {
            void refetch();
          },
        },
      });
      lastToastMessageRef.current = message;
      initialErrorRef.current = null;
    }
  }, [refetch]);

  useEffect(() => {
    if (queryError) {
      const message =
        queryError.detail ??
        queryError.message ??
        "Unable to refresh the FightWeb graph.";
      setSidebarError(message);
      if (lastToastMessageRef.current !== message) {
        toast.error(message, {
          duration: 6000,
          action: {
            label: "Retry",
            onClick: () => {
              void refetch();
            },
          },
        });
        lastToastMessageRef.current = message;
      }
      return;
    }

    if (status === "success") {
      setSidebarError(null);
      lastToastMessageRef.current = null;
    }
  }, [queryError, refetch, status]);

  const applyFilters = useCallback(
    (nextFilters: FightGraphQueryParams) => {
      const normalized = normalizeFilters(
        nextFilters,
        nextFilters.limit ?? defaultFilters.limit ?? fallbackLimit,
      );

      if (filtersEqual(normalized, appliedFilters)) {
        return;
      }

      if (filtersEqual(normalized, defaultFilters)) {
        router.replace(pathname, { scroll: false });
        return;
      }

      const params = createSearchParamsFromFilters(normalized);
      const queryString = params.toString();

      router.replace(
        queryString.length > 0 ? `${pathname}?${queryString}` : pathname,
        { scroll: false },
      );
    },
    [appliedFilters, defaultFilters, fallbackLimit, pathname, router],
  );

  const handleReset = useCallback(() => {
    if (filtersEqual(appliedFilters, defaultFilters)) {
      setSelectedNodeId(null);
      return;
    }
    applyFilters(defaultFilters);
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

  const showInlineError = sidebarError && !graphData;

  return (
    <div className="space-y-10">
      {showInlineError ? (
        <div
          className="rounded-3xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive-foreground"
          role="alert"
        >
          {sidebarError}
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
            isRefreshing={isRefreshing}
            error={sidebarError}
            onRetry={() => {
              void refetch();
            }}
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
            isLoading={isLoading || isFetching}
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
