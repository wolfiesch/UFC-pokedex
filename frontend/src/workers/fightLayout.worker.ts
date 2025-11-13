import {
  forceCenter,
  forceLink,
  forceManyBody,
  forceSimulation,
  type ForceLink,
  type Simulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from "d3-force-3d";

import type {
  FightGraphLink,
  FightGraphNode,
} from "../lib/types";
import type {
  FightLayoutLinkPosition,
  FightLayoutNodePosition,
  FightLayoutProfilingStats,
  FightLayoutWorkerOptions,
  FightLayoutWorkerRequest,
  FightLayoutWorkerResponse,
} from "../types/fight-graph";

export {};

type WorkerNode = SimulationNodeDatum &
  FightGraphNode & {
    id: string;
    degree: number;
    neighbors: Set<string>;
  };

type WorkerLink = SimulationLinkDatum<WorkerNode> &
  FightGraphLink & {
    source: string | WorkerNode;
    target: string | WorkerNode;
  };

const ctx: DedicatedWorkerGlobalScope = self as DedicatedWorkerGlobalScope;

const DEFAULT_OPTIONS: Required<FightLayoutWorkerOptions> = {
  linkDistance: 180,
  chargeStrength: -40,
  updateIntervalMs: 32,
  zScale: 1,
};

const COOLING_ALPHA_THRESHOLD = 0.08;

let simulation: Simulation<WorkerNode, WorkerLink> | null = null;
let nodes: WorkerNode[] = [];
let links: WorkerLink[] = [];
let currentOptions: Required<FightLayoutWorkerOptions> = { ...DEFAULT_OPTIONS };
let lastEmitTimestamp = 0;
let tickCount = 0;
let meanTickMs = 0;
let lastTickDuration = 0;
let emittedStable = false;

function buildWorkerNodes(source: FightGraphNode[], graphLinks: FightGraphLink[]): WorkerNode[] {
  const degreeMap = new Map<string, number>();
  for (const link of graphLinks) {
    degreeMap.set(link.source, (degreeMap.get(link.source) ?? 0) + link.fights);
    degreeMap.set(link.target, (degreeMap.get(link.target) ?? 0) + link.fights);
  }

  return source.map((node) => ({
    ...node,
    id: node.fighter_id,
    degree: degreeMap.get(node.fighter_id) ?? 0,
    x: node.total_fights * Math.cos(node.total_fights),
    y: node.total_fights * Math.sin(node.total_fights),
    z: (node.total_fights % 11) - 5,
    vx: 0,
    vy: 0,
    vz: 0,
    neighbors: new Set<string>(),
  }));
}

function buildWorkerLinks(graphLinks: FightGraphLink[]): WorkerLink[] {
  return graphLinks.map((link) => ({
    ...link,
    source: link.source,
    target: link.target,
  }));
}

function emitUpdate(type: FightLayoutWorkerResponse["type"], alpha: number): void {
  const positions: FightLayoutNodePosition[] = nodes.map((node) => ({
    id: node.id,
    name: node.name,
    division: node.division,
    record: node.record,
    image_url: node.image_url,
    total_fights: node.total_fights,
    latest_event_date: node.latest_event_date,
    x: node.x ?? 0,
    y: node.y ?? 0,
    z: (node.z ?? 0) * currentOptions.zScale,
    vx: node.vx ?? 0,
    vy: node.vy ?? 0,
    vz: node.vz ?? 0,
    degree: node.degree,
  }));

  const linkPositions: FightLayoutLinkPosition[] = links.map((link) => ({
    source: typeof link.source === "string" ? link.source : link.source.id,
    target: typeof link.target === "string" ? link.target : link.target.id,
    fights: link.fights,
    first_event_name: link.first_event_name,
    first_event_date: link.first_event_date,
    last_event_name: link.last_event_name,
    last_event_date: link.last_event_date,
    result_breakdown: link.result_breakdown,
  }));

  const stats: FightLayoutProfilingStats = {
    tickCount,
    meanTickMs,
    lastTickMs: lastTickDuration,
    alpha,
  };

  const payload: FightLayoutWorkerResponse = {
    type,
    nodes: positions,
    links: linkPositions,
    stats,
    timestamp: Date.now(),
  };

  ctx.postMessage(payload);
}

function resetSimulation(
  rawNodes: FightGraphNode[],
  rawLinks: FightGraphLink[],
  options: FightLayoutWorkerOptions | undefined,
): void {
  currentOptions = { ...DEFAULT_OPTIONS, ...(options ?? {}) };

  nodes = buildWorkerNodes(rawNodes, rawLinks);
  links = buildWorkerLinks(rawLinks);

  if (simulation) {
    simulation.stop();
  }

  const linkForce: ForceLink<WorkerNode, WorkerLink> = forceLink<WorkerNode, WorkerLink>(
    links,
  )
    .id((node) => node.id)
    .distance(currentOptions.linkDistance)
    .strength((link) => Math.max(0.02, Math.min(1, link.fights / 5)));

  simulation = forceSimulation<WorkerNode>(nodes)
    .alphaDecay(0.07)
    .velocityDecay(0.4)
    .force("charge", forceManyBody().strength(currentOptions.chargeStrength))
    .force("link", linkForce)
    .force("center", forceCenter(0, 0, 0));

  simulation.on("tick", () => {
    const tickStart = performance.now();
    tickCount += 1;

    const now = performance.now();
    const elapsed = now - lastEmitTimestamp;

    if (elapsed >= currentOptions.updateIntervalMs) {
      lastEmitTimestamp = now;
      emitUpdate("TICK", simulation?.alpha() ?? 0);
      emittedStable = false;
    }

    if (!emittedStable && (simulation?.alpha() ?? 0) < COOLING_ALPHA_THRESHOLD) {
      emittedStable = true;
      emitUpdate("STABLE", simulation?.alpha() ?? 0);
    }

    const tickEnd = performance.now();
    lastTickDuration = tickEnd - tickStart;
    meanTickMs = meanTickMs + (lastTickDuration - meanTickMs) / tickCount;
  });
}

function updateSimulationOptions(options: FightLayoutWorkerOptions): void {
  currentOptions = { ...currentOptions, ...options };

  if (!simulation) {
    return;
  }

  const linkForce = simulation.force("link") as ForceLink<WorkerNode, WorkerLink> | null;
  if (linkForce) {
    if (typeof currentOptions.linkDistance === "number") {
      linkForce.distance(currentOptions.linkDistance);
    }
  }

  const chargeForce = simulation.force("charge");
  if (chargeForce && "strength" in chargeForce) {
    (chargeForce as ReturnType<typeof forceManyBody>).strength(
      currentOptions.chargeStrength,
    );
  }
}

ctx.onmessage = (event: MessageEvent<FightLayoutWorkerRequest>) => {
  const message = event.data;
  switch (message.type) {
    case "INIT":
      tickCount = 0;
      meanTickMs = 0;
      lastEmitTimestamp = 0;
      lastTickDuration = 0;
      emittedStable = false;
      resetSimulation(message.nodes, message.links, message.options);
      break;
    case "UPDATE_OPTIONS":
      updateSimulationOptions(message.options);
      break;
    case "TERMINATE":
      simulation?.stop();
      simulation = null;
      nodes = [];
      links = [];
      break;
    default:
      // Exhaustive check ensures future message types trigger TypeScript errors.
      message satisfies never;
  }
};
