import type { PropsWithChildren, ReactNode } from "react";

import type { TrendPoint } from "@/types/fight-scatter";

import { useTrendWorker } from "./hooks/useTrendWorker";

interface TrendWorkerProviderProps {
  /** Enable or disable trend smoothing entirely. */
  enabled: boolean;
  /** Raw points to smooth. */
  points: TrendPoint[];
  /** Rolling median window size. */
  windowSize?: number;
  /** Render prop receiving the computed trend state. */
  children: (state: TrendWorkerRenderState) => ReactNode;
}

export interface TrendWorkerRenderState {
  trendPoints: TrendPoint[];
  isWorkerAvailable: boolean;
}

/**
 * Headless provider that encapsulates the trend worker lifecycle while keeping
 * consumers declarative via a simple render prop.
 */
export function TrendWorkerProvider({
  enabled,
  points,
  windowSize = 7,
  children,
}: PropsWithChildren<TrendWorkerProviderProps>): ReactNode {
  const state = useTrendWorker({ enabled, points, windowSize });
  return children(state);
}
