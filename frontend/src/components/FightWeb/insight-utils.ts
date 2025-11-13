import type {
  FightGraphLink,
  FightGraphNode,
  FightGraphResponse,
} from "@/lib/types";

/**
 * Representation of derived network insights passed to various FightWeb widgets.
 */
export interface FightWebInsights {
  averageFightsPerFighter: number;
  networkDensity: number;
  divisionBreakdown: DivisionBreakdownEntry[];
  topFighters: FighterHubInsight[];
  busiestRivalries: RivalryInsight[];
}

export interface DivisionBreakdownEntry {
  division: string;
  count: number;
  percentage: number;
}

export interface FighterHubInsight {
  fighterId: string;
  name: string;
  division: string | null | undefined;
  totalFights: number;
  degree: number;
}

export interface RivalryInsight {
  source: string;
  target: string;
  sourceName: string | null;
  targetName: string | null;
  fights: number;
  lastEventName: string | null | undefined;
  lastEventDate: string | null | undefined;
}

type MetadataRecord = Record<string, unknown>;

function isRecord(value: unknown): value is MetadataRecord {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function defaultInsights(): FightWebInsights {
  return {
    averageFightsPerFighter: 0,
    networkDensity: 0,
    divisionBreakdown: [],
    topFighters: [],
    busiestRivalries: [],
  };
}

function calculateNetworkDensity(nodeCount: number, linkCount: number): number {
  if (nodeCount <= 1) {
    return 0;
  }
  const maxEdges = (nodeCount * (nodeCount - 1)) / 2;
  if (maxEdges <= 0) {
    return 0;
  }
  return Number(Math.min(1, Math.max(0, linkCount / maxEdges)).toFixed(4));
}

function deriveDegreeMap(links: FightGraphLink[]): Map<string, number> {
  const degree = new Map<string, number>();
  for (const link of links) {
    degree.set(link.source, (degree.get(link.source) ?? 0) + 1);
    degree.set(link.target, (degree.get(link.target) ?? 0) + 1);
  }
  return degree;
}

function deriveDivisionBreakdown(
  nodes: FightGraphNode[],
): DivisionBreakdownEntry[] {
  if (nodes.length === 0) {
    return [];
  }

  const counts = new Map<string, number>();
  for (const node of nodes) {
    const division = (node.division ?? "Unknown").trim() || "Unknown";
    counts.set(division, (counts.get(division) ?? 0) + 1);
  }

  const total =
    Array.from(counts.values()).reduce((acc, count) => acc + count, 0) || 1;
  return Array.from(counts.entries())
    .map(([division, count]) => ({
      division,
      count,
      percentage: Number(((count / total) * 100).toFixed(1)),
    }))
    .sort((a, b) => b.count - a.count);
}

function deriveTopFighters(
  nodes: FightGraphNode[],
  degree: Map<string, number>,
): FighterHubInsight[] {
  return [...nodes]
    .map((node) => ({
      fighterId: node.fighter_id,
      name: node.name,
      division: node.division,
      totalFights: node.total_fights,
      degree: degree.get(node.fighter_id) ?? 0,
    }))
    .sort((a, b) => {
      if (b.totalFights === a.totalFights) {
        return b.degree - a.degree;
      }
      return b.totalFights - a.totalFights;
    })
    .slice(0, 5);
}

function deriveRivalries(
  links: FightGraphLink[],
  nodeLookup: Map<string, FightGraphNode>,
): RivalryInsight[] {
  return [...links]
    .sort((a, b) => b.fights - a.fights)
    .slice(0, 5)
    .map((link) => {
      const source = nodeLookup.get(link.source);
      const target = nodeLookup.get(link.target);
      return {
        source: link.source,
        target: link.target,
        sourceName: source?.name ?? null,
        targetName: target?.name ?? null,
        fights: link.fights,
        lastEventName: link.last_event_name ?? null,
        lastEventDate: link.last_event_date ?? null,
      };
    });
}

/**
 * Extract useful, presentation-friendly insights from the fight graph payload.
 */
export function extractFightWebInsights(
  graph: FightGraphResponse | null,
  sortedNodes?: FightGraphNode[],
): FightWebInsights {
  if (!graph) {
    return defaultInsights();
  }

  const metadata = isRecord(graph.metadata) ? graph.metadata : {};
  const metadataInsights = isRecord(metadata.insights)
    ? (metadata.insights as MetadataRecord)
    : null;

  if (metadataInsights) {
    const networkDensity =
      Number(metadataInsights["network_density"] ?? 0) || 0;
    const averageFights =
      Number(metadataInsights["average_fights_per_fighter"] ?? 0) || 0;
    const divisionBreakdownRaw = Array.isArray(
      metadataInsights["division_breakdown"],
    )
      ? (metadataInsights["division_breakdown"] as MetadataRecord[])
      : [];
    const topFightersRaw = Array.isArray(metadataInsights["top_fighters"])
      ? (metadataInsights["top_fighters"] as MetadataRecord[])
      : [];
    const rivalriesRaw = Array.isArray(metadataInsights["busiest_rivalries"])
      ? (metadataInsights["busiest_rivalries"] as MetadataRecord[])
      : [];

    const divisionBreakdown = divisionBreakdownRaw
      .map((item) => ({
        division:
          typeof item.division === "string" && item.division.length > 0
            ? item.division
            : "Unknown",
        count: typeof item.count === "number" ? item.count : 0,
        percentage:
          typeof item.percentage === "number"
            ? Number(item.percentage.toFixed(1))
            : 0,
      }))
      .filter((entry) => entry.count > 0)
      .sort((a, b) => b.count - a.count);

    const topFighters = topFightersRaw
      .map((item) => ({
        fighterId: typeof item.fighter_id === "string" ? item.fighter_id : "",
        name: typeof item.name === "string" ? item.name : "Unknown",
        division: typeof item.division === "string" ? item.division : null,
        totalFights:
          typeof item.total_fights === "number" ? item.total_fights : 0,
        degree: typeof item.degree === "number" ? item.degree : 0,
      }))
      .filter((entry) => entry.fighterId.length > 0)
      .sort((a, b) => {
        if (b.totalFights === a.totalFights) {
          return b.degree - a.degree;
        }
        return b.totalFights - a.totalFights;
      })
      .slice(0, 5);

    const busiestRivalries = rivalriesRaw
      .map((item) => ({
        source: typeof item.source === "string" ? item.source : "",
        target: typeof item.target === "string" ? item.target : "",
        sourceName:
          typeof item.source_name === "string" ? item.source_name : null,
        targetName:
          typeof item.target_name === "string" ? item.target_name : null,
        fights: typeof item.fights === "number" ? item.fights : 0,
        lastEventName:
          typeof item.last_event_name === "string"
            ? item.last_event_name
            : (item.last_event_name as string | null | undefined),
        lastEventDate:
          typeof item.last_event_date === "string"
            ? item.last_event_date
            : null,
      }))
      .filter((entry) => entry.source.length > 0 && entry.target.length > 0)
      .sort((a, b) => b.fights - a.fights)
      .slice(0, 5);

    return {
      averageFightsPerFighter: Number(averageFights.toFixed(2)),
      networkDensity: Number(networkDensity.toFixed(4)),
      divisionBreakdown,
      topFighters,
      busiestRivalries,
    };
  }

  const nodes = sortedNodes && sortedNodes.length > 0 ? sortedNodes : graph.nodes;
  const nodeLookup = new Map(nodes.map((node) => [node.fighter_id, node]));
  const degreeMap = deriveDegreeMap(graph.links);
  const totalFights = nodes.reduce((acc, node) => acc + node.total_fights, 0);

  return {
    averageFightsPerFighter: Number(
      (totalFights / Math.max(1, nodes.length)).toFixed(2),
    ),
    networkDensity: calculateNetworkDensity(
      nodes.length,
      graph.links.length,
    ),
    divisionBreakdown: deriveDivisionBreakdown(nodes),
    topFighters: deriveTopFighters(nodes, degreeMap),
    busiestRivalries: deriveRivalries(graph.links, nodeLookup),
  };
}
