import type {
  FightGraphLink,
  FightGraphNode,
  FightGraphResponse,
} from "@/lib/types";

const COLOR_PALETTE = [
  "#2563eb",
  "#f97316",
  "#10b981",
  "#a855f7",
  "#ec4899",
  "#facc15",
  "#14b8a6",
  "#f43f5e",
  "#0ea5e9",
  "#22c55e",
];

export const DEFAULT_NODE_COLOR = "#64748b";

export interface LayoutNode extends FightGraphNode {
  id: string;
  x: number;
  y: number;
  degree: number;
  neighbors: string[];
}

export interface LayoutEdge extends FightGraphLink {}

export interface ForceLayoutOptions {
  iterations?: number;
  repulsionStrength?: number;
  linkDistance?: number;
  springStrength?: number;
  damping?: number;
  centerStrength?: number;
  timeStep?: number;
}

interface MutableNode {
  id: string;
  source: FightGraphNode;
  x: number;
  y: number;
  vx: number;
  vy: number;
  ax: number;
  ay: number;
  neighbors: Set<string>;
}

const EPSILON = 1e-3;

export function computeForceLayout(
  nodes: FightGraphNode[],
  links: FightGraphLink[],
  options: ForceLayoutOptions = {},
): {
  nodes: LayoutNode[];
  edges: LayoutEdge[];
  bounds: { minX: number; maxX: number; minY: number; maxY: number };
} {
  if (nodes.length === 0) {
    return {
      nodes: [],
      edges: [],
      bounds: { minX: 0, maxX: 0, minY: 0, maxY: 0 },
    };
  }

  const iterations =
    options.iterations ?? Math.min(280, Math.max(120, nodes.length * 4));
  const repulsionStrength = options.repulsionStrength ?? 2000; // Increased from 1400
  const linkDistance = options.linkDistance ?? 180; // Increased from 140 (more spacing)
  const springStrength = options.springStrength ?? 0.06; // Reduced from 0.08 (softer springs)
  const damping = options.damping ?? 0.6;
  const centerStrength = options.centerStrength ?? 0.005;
  const timeStep = options.timeStep ?? 0.4;

  const mutableNodes: MutableNode[] = nodes.map((node, index) => {
    const angle = (index / Math.max(1, nodes.length)) * Math.PI * 2;
    const radius = 200 + nodes.length * 1.5;
    return {
      id: node.fighter_id,
      source: node,
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
      vx: 0,
      vy: 0,
      ax: 0,
      ay: 0,
      neighbors: new Set<string>(),
    };
  });

  const lookup = new Map<string, MutableNode>();
  for (const node of mutableNodes) {
    lookup.set(node.id, node);
  }

  const filteredLinks: FightGraphLink[] = [];
  for (const link of links) {
    const source = lookup.get(link.source);
    const target = lookup.get(link.target);
    if (!source || !target || source.id === target.id) {
      continue;
    }
    source.neighbors.add(target.id);
    target.neighbors.add(source.id);
    filteredLinks.push(link);
  }

  for (let iteration = 0; iteration < iterations; iteration++) {
    for (const node of mutableNodes) {
      node.ax = 0;
      node.ay = 0;
    }

    // Repulsive force (Coulomb) between nodes
    for (let i = 0; i < mutableNodes.length; i++) {
      const nodeA = mutableNodes[i];
      for (let j = i + 1; j < mutableNodes.length; j++) {
        const nodeB = mutableNodes[j];
        let dx = nodeB.x - nodeA.x;
        let dy = nodeB.y - nodeA.y;
        let distanceSq = dx * dx + dy * dy + EPSILON;
        const distance = Math.sqrt(distanceSq);
        const force = repulsionStrength / distanceSq;
        dx /= distance;
        dy /= distance;
        nodeA.ax -= force * dx;
        nodeA.ay -= force * dy;
        nodeB.ax += force * dx;
        nodeB.ay += force * dy;
      }
    }

    // Spring force along edges
    for (const link of filteredLinks) {
      const source = lookup.get(link.source);
      const target = lookup.get(link.target);
      if (!source || !target) {
        continue;
      }
      let dx = target.x - source.x;
      let dy = target.y - source.y;
      const distance = Math.sqrt(dx * dx + dy * dy) || EPSILON;
      const displacement = distance - linkDistance;
      const force = springStrength * displacement;
      dx /= distance;
      dy /= distance;
      source.ax += force * dx;
      source.ay += force * dy;
      target.ax -= force * dx;
      target.ay -= force * dy;
    }

    // Pull nodes toward center to keep graph within view
    for (const node of mutableNodes) {
      node.ax -= node.x * centerStrength;
      node.ay -= node.y * centerStrength;
    }

    // Integrate velocity and position
    for (const node of mutableNodes) {
      node.vx = (node.vx + node.ax * timeStep) * damping;
      node.vy = (node.vy + node.ay * timeStep) * damping;
      node.x += node.vx * timeStep;
      node.y += node.vy * timeStep;
    }
  }

  let minX = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;

  for (const node of mutableNodes) {
    if (node.x < minX) minX = node.x;
    if (node.x > maxX) maxX = node.x;
    if (node.y < minY) minY = node.y;
    if (node.y > maxY) maxY = node.y;
  }

  if (!Number.isFinite(minX)) {
    minX = -1;
  }
  if (!Number.isFinite(maxX)) {
    maxX = 1;
  }
  if (!Number.isFinite(minY)) {
    minY = -1;
  }
  if (!Number.isFinite(maxY)) {
    maxY = 1;
  }

  // Avoid zero-size bounds to prevent division by zero during scaling
  if (Math.abs(maxX - minX) < EPSILON) {
    minX -= 1;
    maxX += 1;
  }
  if (Math.abs(maxY - minY) < EPSILON) {
    minY -= 1;
    maxY += 1;
  }

  const layoutNodes: LayoutNode[] = mutableNodes.map((node) => ({
    ...node.source,
    id: node.id,
    x: node.x,
    y: node.y,
    degree: node.neighbors.size,
    neighbors: Array.from(node.neighbors),
  }));

  return {
    nodes: layoutNodes,
    edges: filteredLinks.slice(),
    bounds: { minX, maxX, minY, maxY },
  };
}

export function createDivisionColorScale(
  nodes: FightGraphNode[],
): Map<string, string> {
  const palette = new Map<string, string>();
  let paletteIndex = 0;

  for (const node of nodes) {
    const division =
      node.division && node.division.trim().length > 0
        ? node.division.trim()
        : null;
    if (!division || palette.has(division)) {
      continue;
    }
    palette.set(division, COLOR_PALETTE[paletteIndex % COLOR_PALETTE.length]);
    paletteIndex += 1;
  }

  return palette;
}

export function colorForDivision(
  division: string | null | undefined,
  palette: Map<string, string>,
): string {
  if (!division) {
    return DEFAULT_NODE_COLOR;
  }
  return palette.get(division) ?? DEFAULT_NODE_COLOR;
}

/**
 * Convert hex color to HSL
 */
function hexToHsl(hex: string): { h: number; s: number; l: number } | null {
  // Remove # if present
  const cleanHex = hex.replace("#", "");
  const r = Number.parseInt(cleanHex.substring(0, 2), 16) / 255;
  const g = Number.parseInt(cleanHex.substring(2, 4), 16) / 255;
  const b = Number.parseInt(cleanHex.substring(4, 6), 16) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r:
        h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
        break;
      case g:
        h = ((b - r) / d + 2) / 6;
        break;
      case b:
        h = ((r - g) / d + 4) / 6;
        break;
    }
  }

  return { h: h * 360, s, l };
}

/**
 * Convert HSL to hex color
 */
function hslToHex(h: number, s: number, l: number): string {
  let r: number;
  let g: number;
  let b: number;

  if (s === 0) {
    r = g = b = l; // achromatic
  } else {
    const hue2rgb = (p: number, q: number, t: number): number => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1 / 6) return p + (q - p) * 6 * t;
      if (t < 1 / 2) return q;
      if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
      return p;
    };

    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h / 360 + 1 / 3);
    g = hue2rgb(p, q, h / 360);
    b = hue2rgb(p, q, h / 360 - 1 / 3);
  }

  const toHex = (x: number): string => {
    const hex = Math.round(x * 255).toString(16);
    return hex.length === 1 ? "0" + hex : hex;
  };

  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

/**
 * Create a color scale based on fight recency (latest_event_date).
 * Maps fighter IDs to colors where more recent dates get brighter colors
 * and older dates get dimmer colors, using the division's base color as the hue.
 */
export function createRecencyColorScale(
  nodes: FightGraphNode[],
  divisionColor: string,
): Map<string, string> {
  const colorMap = new Map<string, string>();

  if (nodes.length === 0) {
    return colorMap;
  }

  // Parse dates and find range
  const dates: Array<{ id: string; timestamp: number }> = [];

  for (const node of nodes) {
    if (!node.latest_event_date) {
      continue;
    }

    try {
      const date = new Date(node.latest_event_date);
      if (!Number.isNaN(date.getTime())) {
        dates.push({
          id: node.fighter_id,
          timestamp: date.getTime(),
        });
      }
    } catch {
      // Invalid date, skip
    }
  }

  if (dates.length === 0) {
    // No valid dates, return default color for all nodes
    for (const node of nodes) {
      colorMap.set(node.fighter_id, divisionColor);
    }
    return colorMap;
  }

  // Find min and max timestamps
  const timestamps = dates.map((d) => d.timestamp);
  const minTimestamp = Math.min(...timestamps);
  const maxTimestamp = Math.max(...timestamps);
  const dateRange = maxTimestamp - minTimestamp;

  // Convert base color to HSL
  const baseHsl = hexToHsl(divisionColor);
  if (!baseHsl) {
    // Fallback if color conversion fails
    for (const node of nodes) {
      colorMap.set(node.fighter_id, divisionColor);
    }
    return colorMap;
  }

  // Calculate recency-based colors
  for (const node of nodes) {
    const dateEntry = dates.find((d) => d.id === node.fighter_id);
    if (!dateEntry) {
      // Missing date - use dimmed color
      colorMap.set(
        node.fighter_id,
        hslToHex(baseHsl.h, baseHsl.s * 0.3, baseHsl.l * 0.4),
      );
      continue;
    }

    // Normalize timestamp to 0-1 (1 = most recent, 0 = oldest)
    const normalized =
      dateRange > 0 ? (dateEntry.timestamp - minTimestamp) / dateRange : 1;

    // Map recency to lightness and saturation:
    // Recent (high normalized): high saturation, high lightness
    // Old (low normalized): low saturation, low lightness
    // Use a non-linear curve for better visual distinction
    const recencyFactor = Math.pow(normalized, 0.7); // Slight curve

    // Adjust saturation: 0.3 (dim) to 1.0 (full)
    const saturation = 0.3 + recencyFactor * 0.7;
    // Adjust lightness: 0.35 (dark) to 0.65 (bright) - keeping within readable range
    const lightness = 0.35 + recencyFactor * 0.3;

    const color = hslToHex(baseHsl.h, saturation, lightness);
    colorMap.set(node.fighter_id, color);
  }

  // Handle nodes without dates
  for (const node of nodes) {
    if (!colorMap.has(node.fighter_id)) {
      colorMap.set(
        node.fighter_id,
        hslToHex(baseHsl.h, baseHsl.s * 0.3, baseHsl.l * 0.4),
      );
    }
  }

  return colorMap;
}

function parseYear(value: unknown): number | null {
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    return value.getFullYear();
  }
  if (typeof value === "string" && value.length >= 4) {
    const parsedDate = new Date(value);
    if (!Number.isNaN(parsedDate.getTime())) {
      return parsedDate.getFullYear();
    }
    const numeric = Number.parseInt(value.slice(0, 4), 10);
    return Number.isNaN(numeric) ? null : numeric;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  return null;
}

export function deriveEventYearBounds(
  graph: FightGraphResponse | null,
): { min: number; max: number } | null {
  if (!graph) {
    return null;
  }

  const metadata = graph.metadata ?? {};
  const eventWindowRaw = (metadata as Record<string, unknown>)["event_window"];
  if (
    eventWindowRaw &&
    typeof eventWindowRaw === "object" &&
    !Array.isArray(eventWindowRaw)
  ) {
    const eventWindow = eventWindowRaw as Record<string, unknown>;
    const minYear = parseYear(eventWindow["start"]);
    const maxYear = parseYear(eventWindow["end"]);
    if (minYear !== null && maxYear !== null) {
      return { min: minYear, max: maxYear };
    }
  }

  let minYear: number | null = null;
  let maxYear: number | null = null;

  for (const link of graph.links) {
    const firstYear = parseYear(link.first_event_date);
    const lastYear = parseYear(link.last_event_date);
    if (firstYear !== null) {
      minYear = minYear === null ? firstYear : Math.min(minYear, firstYear);
    }
    if (lastYear !== null) {
      maxYear = maxYear === null ? lastYear : Math.max(maxYear, lastYear);
    }
  }

  if (minYear !== null && maxYear !== null) {
    return { min: minYear, max: maxYear };
  }

  return null;
}
