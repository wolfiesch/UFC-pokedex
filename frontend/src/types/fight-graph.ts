import type { FightGraphLink, FightGraphNode } from "../lib/types";

/**
 * Configuration accepted by the fight layout Web Worker when initialising or
 * updating the simulation. These options are tuned to balance clarity with
 * rendering performance on mid-tier GPUs while keeping the API intentionally
 * narrow.
 */
export interface FightLayoutWorkerOptions {
  /** Base distance targeted by link springs within the force simulation. */
  linkDistance?: number;
  /** Strength of the many-body repulsion force that prevents dense clusters. */
  chargeStrength?: number;
  /**
   * How frequently the worker streams layout updates back to the main thread.
   * Lower numbers create smoother animations at the cost of extra work.
   */
  updateIntervalMs?: number;
  /** Optional z-axis scaling factor applied inside the worker for stability. */
  zScale?: number;
}

/**
 * Request message contract consumed by the layout worker.
 */
export type FightLayoutWorkerRequest =
  | {
      type: "INIT";
      nodes: FightGraphNode[];
      links: FightGraphLink[];
      options?: FightLayoutWorkerOptions;
    }
  | {
      type: "UPDATE_OPTIONS";
      options: FightLayoutWorkerOptions;
    }
  | {
      type: "TERMINATE";
    };

/**
 * Node payload returned from the layout worker on each tick. The worker keeps
 * velocity information so the renderer can apply inertia-based easing.
 */
export interface FightLayoutNodePosition extends FightGraphNode {
  id: string;
  x: number;
  y: number;
  z: number;
  vx: number;
  vy: number;
  vz: number;
  degree: number;
}

/** Lightweight link payload mirrored from the API response. */
export interface FightLayoutLinkPosition extends FightGraphLink {
  source: string;
  target: string;
}

/**
 * Summary of the layout simulation used for rudimentary profiling on the UI
 * thread. The numbers help adapt the force parameters when the frame rate
 * starts to dip.
 */
export interface FightLayoutProfilingStats {
  /** Number of simulation ticks processed since the last reset. */
  tickCount: number;
  /** Average execution time for a single force tick in milliseconds. */
  meanTickMs: number;
  /** Duration of the most recent tick in milliseconds. */
  lastTickMs: number;
  /** Current alpha value emitted from the d3-force simulation. */
  alpha: number;
}

/**
 * Messages emitted by the worker. Updates stream tick-by-tick while "STABLE"
 * indicates that alpha has cooled below the configured threshold.
 */
export type FightLayoutWorkerResponse =
  | {
      type: "TICK";
      nodes: FightLayoutNodePosition[];
      links: FightLayoutLinkPosition[];
      stats: FightLayoutProfilingStats;
      timestamp: number;
    }
  | {
      type: "STABLE";
      nodes: FightLayoutNodePosition[];
      links: FightLayoutLinkPosition[];
      stats: FightLayoutProfilingStats;
      timestamp: number;
    };
