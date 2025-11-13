import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";

import { getFightGraph } from "@/lib/api";
import type {
  FightGraphQueryParams,
  FightGraphResponse,
} from "@/types/fight-graph";

interface UseFightGraphOptions {
  /** Initial filters applied to the aggregation. */
  initialParams?: FightGraphQueryParams;
  /** Flag enabling automatic fetch on mount. */
  autoFetch?: boolean;
}

interface UseFightGraphResult {
  data: FightGraphResponse | null;
  isLoading: boolean;
  error: Error | null;
  params: FightGraphQueryParams;
  setParams: Dispatch<SetStateAction<FightGraphQueryParams>>;
  refetch: () => Promise<void>;
}

/**
 * Declarative React hook that wraps the fight graph REST request.
 *
 * The hook tracks loading and error state, memoises the currently
 * selected filters, and exposes an imperative `refetch` helper so
 * forms can re-run the query without triggering duplicate requests.
 */
export function useFightGraph(
  options: UseFightGraphOptions = {},
): UseFightGraphResult {
  const { initialParams = {}, autoFetch = true } = options;

  const [params, setParams] = useState<FightGraphQueryParams>(initialParams);
  const [data, setData] = useState<FightGraphResponse | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const memoizedParams = useMemo(() => ({ ...params }), [params]);

  const fetchGraph = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await getFightGraph(memoizedParams);
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, [memoizedParams]);

  useEffect(() => {
    if (!autoFetch) {
      return;
    }
    void fetchGraph();
  }, [autoFetch, fetchGraph, memoizedParams]);

  return {
    data,
    isLoading,
    error,
    params: memoizedParams,
    setParams,
    refetch: fetchGraph,
  };
}
